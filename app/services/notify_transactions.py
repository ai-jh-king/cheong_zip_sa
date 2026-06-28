"""관심 단지/지역 신규 실거래 알림.

수집(collect_live)으로 새 실거래가 적재되면, 그 단지/지역을 관심등록한 '로그인 사용자'에게
알림(Notification, type="transaction")을 생성한다.

설계(왜곡 없음·확장성):
  - 멱등/중복 방지: app_meta 의 커서(notify_last_tx_id) 이후의 거래만 1회 처리하고 커서를 전진.
    → 수집이 매일 돌아도 같은 거래로 두 번 알리지 않음. 커서 이전(관심등록 전) 거래는 알리지 않음(의도).
  - 집합 매칭(N+1 회피): 신규 거래에서 대상 키를 모아 Favorite 을 IN 으로 한 번에 조회.
  - 대상별 그룹화: 한 단지에 N건이 들어와도 사용자당 "새 실거래 N건" 1건으로.
  - 수신자: Favorite 은 device 기준 → DeviceLink 로 account 연결된 사용자만 알림(비로그인 제외).
  - 사실만: 알림 문구는 '건수'와 단지/지역명만. 가격 전망·과장 없음. is_sample/해제분 제외.

매칭 키(프런트 favId 와 동일 규칙):
  - 단지: target_id = "{단지명}__{lawd_cd}__{property_type}"
  - 지역: target_id = "region:{구명}"  (구명 = _gu_name(lawd_cd) = "청주시 OO구")
"""
from __future__ import annotations
import logging

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import Transaction, Favorite, DeviceLink, Notification
from app.services import appmeta
from app.services.stats import _gu_name

logger = logging.getLogger(__name__)
CURSOR_KEY = "notify_last_tx_id"
MAX_BATCH = 5000  # 한 번에 처리할 신규 거래 상한(폭주 보호)


def _eok(manwon: int) -> str:
    return f"{manwon / 10000:.2f}억"


def _get_cursor(db: Session) -> int:
    return appmeta.get_int(db, CURSOR_KEY, 0)


def _set_cursor(db: Session, value: int) -> None:
    appmeta.set(db, CURSOR_KEY, value, commit=False)


def notify_new_transactions(db: Session) -> dict:
    """커서 이후 신규 실거래를 관심 대상과 매칭해 알림 생성. 처리 요약 반환."""
    cursor = _get_cursor(db)
    new_txs = db.scalars(
        select(Transaction).where(
            Transaction.id > cursor,
            Transaction.is_sample.is_(False),
            Transaction.is_canceled.isnot(True),
            Transaction.complex_name.isnot(None),
        ).order_by(Transaction.id).limit(MAX_BATCH)
    ).all()
    if not new_txs:
        return {"new_tx": 0, "matched_favorites": 0, "notifications": 0}

    max_id = max(t.id for t in new_txs)

    # 신규 거래 → 대상 키 집계
    complex_info: dict[str, dict] = {}
    region_info: dict[str, dict] = {}
    for t in new_txs:
        tid = f"{t.complex_name}__{t.lawd_cd}__{t.property_type}"
        ci = complex_info.setdefault(
            tid, {"count": 0, "name": t.complex_name, "lawd": t.lawd_cd, "ptype": t.property_type})
        ci["count"] += 1
        if t.deal_type == "trade" and t.deal_amount and t.deal_amount > ci.get("new_high", 0):
            ci["new_high"] = t.deal_amount
        gu = _gu_name(t.lawd_cd)
        rk = "region:" + gu
        ri = region_info.setdefault(rk, {"count": 0, "gu": gu, "lawd": t.lawd_cd})
        ri["count"] += 1

    target_ids = list(complex_info.keys()) + list(region_info.keys())
    favs = db.scalars(select(Favorite).where(Favorite.target_id.in_(target_ids))).all()
    if not favs:
        _set_cursor(db, max_id)
        db.commit()
        return {"new_tx": len(new_txs), "matched_favorites": 0, "notifications": 0}

    # device → account 매핑(로그인 사용자만 수신)
    device_ids = {f.device_id for f in favs}
    links = db.scalars(select(DeviceLink).where(DeviceLink.device_id.in_(device_ids))).all()
    dev2acct = {ln.device_id: ln.account_id for ln in links}

    # 신고가 경신 판정: 이번 신규 매매 최고가가 '직전까지(커서 이전) 최고가'를 넘으면 신고가.
    new_high_map: dict[str, dict] = {}
    for tid, info in complex_info.items():
        nh = info.get("new_high")
        if not nh:
            continue
        hist = db.scalar(select(func.max(Transaction.deal_amount)).where(
            Transaction.complex_name == info["name"],
            Transaction.lawd_cd == info["lawd"],
            Transaction.property_type == info["ptype"],
            Transaction.deal_type == "trade",
            Transaction.deal_amount.isnot(None),
            Transaction.is_sample.is_(False),
            Transaction.is_canceled.isnot(True),
            Transaction.id <= cursor,
        ))
        if hist is not None and nh > hist:
            new_high_map[tid] = {"new_high": nh, "prev": hist}

    made = 0
    pushes: list[tuple[int, dict]] = []   # (account_id, payload) 커밋 후 발송
    seen: set[tuple[int, str]] = set()   # (account_id, target_id) 중복 방지(여러 device 합산)
    for f in favs:
        acct = dev2acct.get(f.device_id)
        if not acct:
            continue  # 비로그인 device → 영속 알림 대상 아님
        key = (acct, f.target_id)
        if key in seen:
            continue
        seen.add(key)
        if f.target_type == "complex" and f.target_id in complex_info:
            info = complex_info[f.target_id]
            if f.target_id in new_high_map:
                nh = new_high_map[f.target_id]
                msg = f"관심 단지 '{info['name']}' 신고가 경신 {_eok(nh['new_high'])} (직전 최고 {_eok(nh['prev'])})"
                db.add(Notification(
                    account_id=acct, type="new_high", message=msg,
                    complex_name=info["name"], lawd_cd=info["lawd"], property_type=info["ptype"]))
                pushes.append((acct, {"title": "신고가 경신 🚀", "body": msg, "url": "/"}))
            else:
                msg = f"관심 단지 '{info['name']}'에 새 실거래 {info['count']}건"
                db.add(Notification(
                    account_id=acct, type="transaction", message=msg,
                    complex_name=info["name"], lawd_cd=info["lawd"], property_type=info["ptype"]))
                pushes.append((acct, {"title": "새 실거래 🏷️", "body": msg, "url": "/"}))
            made += 1
        elif f.target_type == "region" and f.target_id in region_info:
            info = region_info[f.target_id]
            msg = f"관심 지역 '{info['gu']}'에 새 실거래 {info['count']}건"
            db.add(Notification(
                account_id=acct, type="transaction", message=msg, lawd_cd=info["lawd"]))
            pushes.append((acct, {"title": "새 실거래 🏷️", "body": msg, "url": "/"}))
            made += 1

    _set_cursor(db, max_id)
    db.commit()
    # 푸시 발송(키 없으면 no-op). 실패해도 수집/알림은 영향 없음.
    pushed = 0
    try:
        from app.services import push as _push
        if _push.is_enabled():
            for acct, payload in pushes:
                try:
                    r = _push.dispatch_to_account(db, acct, payload)
                    pushed += r.get("sent", 0)
                except Exception:  # noqa
                    logger.exception("푸시 발송 실패(알림은 정상)")
    except Exception:  # noqa
        logger.exception("푸시 모듈 오류(무시)")
    logger.info("실거래 알림: 신규 %s건 / 알림 %s개 / 신고가 %s개 / 푸시 %s건",
                len(new_txs), made, len(new_high_map), pushed)
    return {"new_tx": len(new_txs), "matched_favorites": len(favs), "notifications": made,
            "new_highs": len(new_high_map), "pushed": pushed}
