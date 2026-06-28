"""독립 스케줄러 — 주기적으로 수집(live)+지오코딩 실행.

배포 시 웹 워커와 분리된 '단일 프로세스'로 실행할 것(중복 실행 방지):
  python -m scripts.scheduler

동작/주기는 .env:
  SCHEDULER_INTERVAL_HOURS (기본 24)
  SCHEDULER_RUN_COLLECT    (기본 true; MOLIT 키 있을 때만 실수집)
외부 의존성 없음(간단 루프). 첫 사이클은 즉시 1회 실행 후 주기 반복.
"""
import logging
import time

from app.core.config import get_settings
from app.db.session import init_db, SessionLocal

logging.basicConfig(level=get_settings().log_level,
                    format="%(asctime)s %(levelname)s [scheduler]: %(message)s")
log = logging.getLogger("scheduler")


def _cycle() -> None:
    s = get_settings()
    from app.services.monitoring import record_job
    with SessionLocal() as db:
        if s.scheduler_run_collect and getattr(s, "molit_enabled", False):
            try:
                from app.pipeline.collect import collect_live
                log.info("수집(live) 시작…")
                log.info("수집 결과: %s", record_job(db, "collect_live", lambda: collect_live(db)))
            except Exception as e:  # noqa
                log.warning("수집 실패: %s", e)   # record_job 이 이미 기록·경보함
        else:
            log.info("수집 건너뜀(키 없음 또는 비활성)")
        try:
            from app.services.geocode import run_geocode, GeocodeKeyMissing

            def _geo():
                try:
                    return run_geocode(db)
                except GeocodeKeyMissing:
                    return {"skipped": "no_key"}
            log.info("지오코딩 결과: %s", record_job(db, "geocode", _geo))
        except Exception as e:  # noqa
            log.warning("지오코딩 실패: %s", e)
        if getattr(s, "scheduler_run_backup", False):
            try:
                from scripts.backup import run_backup
                log.info("백업 결과: %s", record_job(db, "backup", run_backup))
            except Exception as e:  # noqa
                log.warning("백업 실패: %s", e)   # record_job 이 이미 기록·경보함


def main() -> int:
    init_db()
    s = get_settings()
    interval = max(1, s.scheduler_interval_hours) * 3600
    log.info("스케줄러 시작 — 주기 %s시간(웹 워커와 분리된 단일 프로세스로 실행하세요)",
             s.scheduler_interval_hours)
    while True:
        start = time.time()
        try:
            _cycle()
        except Exception as e:  # noqa
            log.warning("사이클 오류: %s", e)
        sleep = max(60, interval - (time.time() - start))
        log.info("다음 실행까지 %s초 대기", int(sleep))
        time.sleep(sleep)


if __name__ == "__main__":
    raise SystemExit(main())
