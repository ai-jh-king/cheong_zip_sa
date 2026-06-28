"""관측성(모니터링) — 배치 실행 기록 + 실패 경보 + 통합 상태.

- record_job: 배치(fn)를 감싸 실행 → JobRun 에 성공/실패/소요/통계 기록, 실패 시 alert.
- alert: 로그(ERROR) + (설정 시) 웹훅(Slack/Discord/일반)으로 경보. 키 없으면 로그만.
- system_status: DB·데이터 신선도·최근 실행·핵심 카운트·경고를 한 번에 반환(모니터링 폴링용).
모두 외부 키 없이도 안전하게 동작(키 게이팅). 개인정보·키 값은 노출하지 않음.
"""
from __future__ import annotations
import logging
import time
from datetime import datetime, date, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import JobRun, Transaction, Complex, PushSubscription, Favorite
from app.services import appmeta

logger = logging.getLogger(__name__)

# 모니터링이 추적하는 알려진 작업들(상태 화면에서 항상 노출)
KNOWN_JOBS = ["collect_live", "geocode", "notify", "backup"]


def alert(subject: str, body: str = "") -> None:
    """실패/이상 경보. 항상 ERROR 로그, 웹훅이 설정돼 있으면 추가 발송."""
    logger.error("ALERT | %s | %s", subject, body)
    url = (get_settings().alert_webhook_url or "").strip()
    if not url:
        return
    try:
        import httpx
        text = f"🚨 {subject}\n{body}" if body else f"🚨 {subject}"
        # Slack=text, Discord=content — 둘 다 보내 호환(미사용 키는 무시됨)
        httpx.post(url, json={"text": text, "content": text}, timeout=8)
    except Exception:  # noqa
        logger.exception("경보 웹훅 발송 실패")


def _finish(db: Session, rid: int, status: str, stats, err, t0: float) -> None:
    run = db.get(JobRun, rid)
    if not run:
        return
    run.status = status
    run.stats = stats if isinstance(stats, dict) else ({"result": str(stats)} if stats is not None else None)
    run.error = err
    run.finished_at = datetime.utcnow()
    run.duration_ms = int((time.monotonic() - t0) * 1000)
    db.commit()


def record_job(db: Session, name: str, fn):
    """fn() 을 실행하며 JobRun 에 기록. 성공 시 결과 반환, 실패 시 경보 후 재발생.

    스케줄러처럼 '계속 진행'이 필요한 호출자는 try/except 로 감싸 사용.
    """
    run = JobRun(name=name, status="running", started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    rid = run.id
    t0 = time.monotonic()
    try:
        res = fn()
    except Exception as e:  # noqa
        db.rollback()
        _finish(db, rid, "fail", None, repr(e)[:500], t0)
        appmeta.set_json(db, f"last_{name}", {"at": _now_iso(), "status": "fail", "error": str(e)[:200]})
        alert(f"[작업 실패] {name}", repr(e))
        raise
    _finish(db, rid, "ok", res, None, t0)
    appmeta.set_json(db, f"last_{name}", {"at": _now_iso(), "status": "ok"})
    return res


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def recent_runs(db: Session, limit: int = 20, name: str | None = None) -> list[dict]:
    stmt = select(JobRun).order_by(JobRun.started_at.desc()).limit(limit)
    if name:
        stmt = select(JobRun).where(JobRun.name == name).order_by(JobRun.started_at.desc()).limit(limit)
    out = []
    for r in db.scalars(stmt).all():
        out.append({
            "id": r.id, "name": r.name, "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_ms": r.duration_ms, "stats": r.stats, "error": r.error,
        })
    return out


def _last_run(db: Session, name: str) -> dict | None:
    r = db.scalar(select(JobRun).where(JobRun.name == name)
                  .order_by(JobRun.started_at.desc()).limit(1))
    if not r:
        return None
    return {"status": r.status, "at": (r.finished_at or r.started_at).isoformat() if (r.finished_at or r.started_at) else None,
            "duration_ms": r.duration_ms, "stats": r.stats, "error": r.error}


def system_status(db: Session) -> dict:
    """모니터링 통합 스냅샷 — 폴링 한 번으로 건강도/경고 파악."""
    s = get_settings()
    warnings: list[str] = []

    db_ok = True
    try:
        db.execute(select(func.count()).select_from(Transaction))
    except Exception:  # noqa
        db_ok = False
        warnings.append("DB 연결 실패")

    latest = stale_days = total_real = None
    if db_ok:
        latest = db.scalar(select(func.max(Transaction.contract_date))
                           .where(Transaction.is_sample.is_(False),
                                  Transaction.is_canceled.isnot(True)))
        total_real = db.scalar(select(func.count()).select_from(
            select(Transaction).where(Transaction.is_sample.is_(False),
                                      Transaction.is_canceled.isnot(True)).subquery())) or 0
        if latest:
            stale_days = (date.today() - latest).days
            if stale_days > s.data_stale_days:
                warnings.append(f"실데이터가 {stale_days}일째 갱신되지 않았습니다")
        elif s.molit_enabled:
            warnings.append("실데이터가 아직 없습니다(수집 필요)")

    last = {j: _last_run(db, j) for j in KNOWN_JOBS} if db_ok else {}
    lc = last.get("collect_live")
    if lc and lc.get("status") == "fail":
        warnings.append("최근 수집(collect_live)이 실패했습니다")
    lb = last.get("backup")
    if lb and lb.get("status") == "fail":
        warnings.append("최근 백업(backup)이 실패했습니다")

    if not s.molit_enabled:
        warnings.append("MOLIT 키 미설정 — 실데이터 수집 비활성")

    counts = {}
    if db_ok:
        counts = {
            "transactions_real": int(total_real or 0),
            "complexes": db.scalar(select(func.count()).select_from(Complex)) or 0,
            "push_subscriptions": db.scalar(select(func.count()).select_from(
                select(PushSubscription).where(PushSubscription.disabled.is_(False)).subquery())) or 0,
            "favorites": db.scalar(select(func.count()).select_from(Favorite)) or 0,
        }

    integrations = {
        "molit": s.molit_enabled,
        "kakao_poi": bool(s.kakao_rest_api_key),
        "map": bool(s.naver_map_client_id),
        "push": s.push_enabled,
        "sentry": bool(s.sentry_dsn),
        "alert_webhook": bool(s.alert_webhook_url),
    }

    return {
        "ok": db_ok and not any(w for w in warnings
                                if "갱신" in w or "DB" in w or "수집(collect_live)" in w
                                or "백업(backup)" in w),
        "checked_at": _now_iso(),
        "db_ok": db_ok,
        "data_as_of": latest.isoformat() if latest else None,
        "data_stale_days": stale_days,
        "last_runs": last,
        "counts": counts,
        "integrations": integrations,
        "warnings": warnings,
    }
