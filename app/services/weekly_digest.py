"""관심단지 주간 다이제스트 — 재방문 엔진(주 1회 푸시+알림함).

설계(왜곡 없음·스팸 없음):
  - 대상: 관심단지(Favorite complex) 보유 + 계정 연결(DeviceLink) 사용자.
  - 내용: 지난 7일 '실제 신고된 거래'만 요약(단지별 건수 + 최근 매매가). 데이터를 만들지 않음.
  - 지난주 거래가 하나도 없으면 그 사용자에겐 **발송하지 않는다**(빈 소식 스팸 금지).
  - 주 1회: 월요일에만 + ISO 주차 마커(app_meta 'last_digest_week')로 멱등
    (스케줄러가 매일 돌아도 실제 발송은 주 1회).
스케줄러(_cycle) 말미에서 호출. 푸시 키 없으면 알림함만 생성(no-op 푸시).
"""
from __future__ import annotations
import logging
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import Favorite, DeviceLink, Notification, Transaction
from app.services import appmeta

logger = logging.getLogger(__name__)

MAX_LINES = 4          # 푸시 본문에 담을 단지 수(나머지는 '외 N곳')
_WEEK_KEY = "last_digest_week"


def _iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _fav_complexes(db: Session) -> list[tuple[int, str, str]]:
    """(account_id, complex_name, lawd_cd) — 계정 연결된 관심단지만."""
    favs = db.scalars(select(Favorite).where(Favorite.target_type == "complex")).all()
    if not favs:
        return []
    dev_ids = list({f.device_id for f in favs})
    links = db.scalars(select(DeviceLink).where(DeviceLink.device_id.in_(dev_ids))).all()
    dev2acct = {ln.device_id: ln.account_id for ln in links}
    out, seen = [], set()
    for f in favs:
        acct = dev2acct.get(f.device_id)
        name = f.name or (f.meta or {}).get("complex_name")
        lawd = (f.meta or {}).get("lawd_cd")
        if not acct or not name or not lawd:
            continue
        key = (acct, name, lawd)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def run(db: Session, force: bool = False, today: date | None = None) -> dict:
    """주간 다이제스트 생성·발송. force=테스트/수동 실행용(요일·주차 가드 무시)."""
    today = today or date.today()
    if not force:
        if today.weekday() != 0:                       # 월요일에만
            return {"skipped": "not_monday"}
        if appmeta.get(db, _WEEK_KEY) == _iso_week(today):
            return {"skipped": "already_sent"}

    since = today - timedelta(days=7)
    targets = _fav_complexes(db)
    if not targets:
        appmeta.set(db, _WEEK_KEY, _iso_week(today))
        return {"accounts": 0, "notifications": 0, "pushed": 0}

    # 관심단지 전체를 한 번에 집계(단지별 지난 7일: 거래수 + 최근 매매가)
    names = list({(n, l) for _, n, l in targets})
    stats: dict[tuple, dict] = {}
    for name, lawd in names:
        rows = db.execute(
            select(func.count(), func.max(Transaction.contract_date))
            .where(Transaction.complex_name == name, Transaction.lawd_cd == lawd,
                   Transaction.contract_date >= since,
                   Transaction.is_sample.is_(False),
                   Transaction.is_canceled.isnot(True))).one()
        cnt = rows[0] or 0
        latest_amt = None
        if cnt:
            latest_amt = db.scalar(
                select(Transaction.deal_amount)
                .where(Transaction.complex_name == name, Transaction.lawd_cd == lawd,
                       Transaction.contract_date >= since, Transaction.deal_type == "trade",
                       Transaction.is_sample.is_(False), Transaction.is_canceled.isnot(True),
                       Transaction.deal_amount.isnot(None))
                .order_by(Transaction.contract_date.desc()).limit(1))
        stats[(name, lawd)] = {"count": cnt, "latest": latest_amt}

    def _eok(v):
        return f"{v / 10000:.1f}억" if v else None

    # 계정별 조립 — 거래 있는 단지만, 없으면 발송 안 함
    by_acct: dict[int, list] = {}
    for acct, name, lawd in targets:
        s = stats.get((name, lawd)) or {}
        if s.get("count"):
            by_acct.setdefault(acct, []).append((name, s["count"], s.get("latest")))

    made = pushed = 0
    pushes = []
    for acct, items in by_acct.items():
        items.sort(key=lambda x: -x[1])
        lines = [f"{n} {c}건" + (f"·최근 {_eok(a)}" if a else "") for n, c, a in items[:MAX_LINES]]
        extra = f" 외 {len(items) - MAX_LINES}곳" if len(items) > MAX_LINES else ""
        msg = "지난주 관심단지 소식: " + ", ".join(lines) + extra
        db.add(Notification(account_id=acct, type="digest", message=msg))
        made += 1
        pushes.append((acct, {"title": "📮 관심단지 주간 소식", "body": msg, "url": "/"}))
    appmeta.set(db, _WEEK_KEY, _iso_week(today))
    db.commit()

    try:
        from app.services import push as _push
        if _push.is_enabled():
            for acct, payload in pushes:
                try:
                    r = _push.dispatch_to_account(db, acct, payload)
                    pushed += r.get("sent", 0)
                except Exception:  # noqa
                    logger.exception("다이제스트 푸시 실패(알림은 정상)")
    except Exception:  # noqa
        logger.exception("푸시 모듈 오류(무시)")
    logger.info("주간 다이제스트: 대상계정 %s / 알림 %s / 푸시 %s", len(by_acct), made, pushed)
    return {"accounts": len(by_acct), "notifications": made, "pushed": pushed}
