"""관심단지·우리집 새 실거래 일간 알림 — 재방문 훅(주간 다이제스트의 일간 버전).

설계(왜곡 없음·스팸 없음):
  - 대상: 계정 연결된 사용자의 **관심단지**(Favorite complex) + **우리집**(UserPref.data.my_home).
  - 트리거: 마지막 발송 이후 **새로 적재된 실거래**(Transaction.id 기준 증가분)만.
    계약일 기준이 아니라 '수집으로 들어온 순간' 기준이라, 신고 지연분이 뒤늦게 들어와도 놓치지 않는다.
  - 새 거래가 없는 사용자에겐 **발송하지 않는다**(빈 소식 금지).
  - 하루 1회: app_meta 'last_daily_alert_date' 마커로 멱등(스케줄러가 여러 번 돌아도 1회).
  - 예시(is_sample)·해제(is_canceled) 거래는 제외.

주간 다이제스트(월요일 요약)와 역할 분담: 이쪽은 '오늘 내 단지에 거래가 떴다'는 즉시성.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DeviceLink, Favorite, Notification, Transaction, UserPref
from app.services import appmeta

logger = logging.getLogger(__name__)

MAX_LINES = 3                       # 알림 본문에 담을 단지 수(나머지는 '외 N곳')
_DATE_KEY = "last_daily_alert_date"
_CURSOR_KEY = "daily_alert_cursor"  # 마지막으로 처리한 Transaction.id


def _watch_list(db: Session) -> list[tuple[int, str, str, bool]]:
    """(account_id, complex_name, lawd_cd, is_home) — 계정 연결된 관심단지 + 우리집."""
    out, seen = [], set()

    def _add(acct, name, lawd, is_home):
        if not acct or not name or not lawd:
            return
        key = (acct, name, lawd)
        if key in seen:
            return
        seen.add(key)
        out.append((acct, name, lawd, is_home))

    favs = db.scalars(select(Favorite).where(Favorite.target_type == "complex")).all()
    prefs = db.scalars(select(UserPref)).all()
    dev_ids = list({f.device_id for f in favs} | {p.device_id for p in prefs})
    dev2acct = {}
    if dev_ids:
        links = db.scalars(select(DeviceLink).where(DeviceLink.device_id.in_(dev_ids))).all()
        dev2acct = {ln.device_id: ln.account_id for ln in links}

    # 우리집이 관심단지보다 중요 → 먼저 등록(중복 시 우리집으로 표시됨)
    for p in prefs:
        home = ((p.data or {}).get("my_home")) or {}
        _add(dev2acct.get(p.device_id), home.get("complex_name"), home.get("lawd_cd"), True)
    for f in favs:
        meta = f.meta or {}
        _add(dev2acct.get(f.device_id), f.name or meta.get("complex_name"),
             meta.get("lawd_cd"), False)
    return out


def _eok(v):
    return f"{v / 10000:.1f}억" if v else None


def run(db: Session, force: bool = False, today: date | None = None) -> dict:
    """새 실거래 알림. force=테스트/수동(하루 1회 가드 무시)."""
    today = today or date.today()
    if not force and appmeta.get(db, _DATE_KEY) == today.isoformat():
        return {"skipped": "already_sent_today"}

    max_id = db.scalar(select(func.max(Transaction.id))) or 0
    cursor = int(appmeta.get(db, _CURSOR_KEY) or 0)
    if max_id <= cursor:                      # 새로 적재된 거래 없음
        appmeta.set(db, _DATE_KEY, today.isoformat())
        return {"accounts": 0, "notifications": 0, "pushed": 0, "new_rows": 0}

    targets = _watch_list(db)
    if not targets:
        appmeta.set(db, _CURSOR_KEY, str(max_id))
        appmeta.set(db, _DATE_KEY, today.isoformat())
        return {"accounts": 0, "notifications": 0, "pushed": 0, "new_rows": max_id - cursor}

    # 신규 적재분 중 관심 단지 것만 집계(단지별 건수 + 최근 매매가)
    watched = {(n, l) for _, n, l, _ in targets}
    rows = db.execute(
        select(Transaction.complex_name, Transaction.lawd_cd, Transaction.deal_type,
               Transaction.deal_amount, Transaction.contract_date)
        .where(Transaction.id > cursor, Transaction.id <= max_id,
               Transaction.complex_name.isnot(None),
               Transaction.is_sample.is_(False),
               Transaction.is_canceled.isnot(True))).all()
    agg: dict[tuple, dict] = {}
    for name, lawd, deal_type, amount, cdate in rows:
        key = (name, lawd)
        if key not in watched:
            continue
        a = agg.setdefault(key, {"count": 0, "latest": None, "latest_date": None})
        a["count"] += 1
        if deal_type == "trade" and amount and (a["latest_date"] is None or
                                                (cdate and cdate >= a["latest_date"])):
            a["latest"], a["latest_date"] = amount, cdate

    by_acct: dict[int, list] = {}
    for acct, name, lawd, is_home in targets:
        a = agg.get((name, lawd))
        if a and a["count"]:
            by_acct.setdefault(acct, []).append((name, a["count"], a["latest"], is_home))

    made = pushed = 0
    pushes = []
    for acct, items in by_acct.items():
        items.sort(key=lambda x: (not x[3], -x[1]))        # 우리집 먼저, 그다음 건수순
        lines = [("🏠 " if home else "") + f"{n} {c}건" + (f"·{_eok(amt)}" if amt else "")
                 for n, c, amt, home in items[:MAX_LINES]]
        extra = f" 외 {len(items) - MAX_LINES}곳" if len(items) > MAX_LINES else ""
        msg = "새 실거래: " + ", ".join(lines) + extra
        db.add(Notification(account_id=acct, type="transaction", message=msg))
        made += 1
        pushes.append((acct, {"title": "🔔 관심단지 새 실거래", "body": msg, "url": "/"}))

    appmeta.set(db, _CURSOR_KEY, str(max_id))
    appmeta.set(db, _DATE_KEY, today.isoformat())
    db.commit()

    try:
        from app.services import push as _push
        if _push.is_enabled():
            for acct, payload in pushes:
                try:
                    pushed += _push.dispatch_to_account(db, acct, payload).get("sent", 0)
                except Exception:  # noqa: BLE001
                    logger.exception("일간 알림 푸시 실패(알림함은 정상)")
    except Exception:  # noqa: BLE001
        logger.exception("푸시 모듈 오류(무시)")

    logger.info("일간 실거래 알림: 계정 %s / 알림 %s / 푸시 %s (신규 %s건)",
                len(by_acct), made, pushed, max_id - cursor)
    return {"accounts": len(by_acct), "notifications": made, "pushed": pushed,
            "new_rows": max_id - cursor}
