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
            from app.services.geocode import run_geocode, run_geocode_places, GeocodeKeyMissing

            def _geo():
                try:
                    # 주소(도로명·지번) 기반 전면 재산출은 배포 후 최초 1회만(멱등 플래그) —
                    # 키워드 오탐 시절 좌표('학교 위 가격핀' 실사고)를 프로드에서 사람 손 없이 청소.
                    # 이후는 revalidate(동 기준점·구 경계 재검증)로 매일 자가치유.
                    from app.services import appmeta
                    first = not appmeta.get(db, "geocode_addr_refresh_v1237")
                    r1 = run_geocode(db, refresh=first, revalidate=not first)   # 단지
                    if first:
                        appmeta.set(db, "geocode_addr_refresh_v1237", "1")
                    r2 = run_geocode_places(db)             # 시설(학원 등 좌표 미제공 소스)
                    return {"complex": r1, "places": r2, "addr_refresh": first}
                except GeocodeKeyMissing:
                    return {"skipped": "no_key"}
            log.info("지오코딩 결과: %s", record_job(db, "geocode", _geo))
        except Exception as e:  # noqa
            log.warning("지오코딩 실패: %s", e)
        # 관심단지 주간 다이제스트(월요일·주 1회 멱등 — 서비스 내부 가드)
        try:
            from app.services import weekly_digest
            res = weekly_digest.run(db)
            if not res.get("skipped"):
                log.info("주간 다이제스트 결과: %s", record_job(db, "weekly_digest", lambda: res))
        except Exception as e:  # noqa
            log.warning("주간 다이제스트 실패: %s", e)
        # 집계 스냅샷 굽기 — 수집/지오코딩으로 데이터가 갱신된 뒤 board/ranking 을 미리 계산해
        # 저장(웹은 요청 시 읽기 1회). 데이터가 하루 1회만 바뀌므로 매 요청 계산 낭비 제거.
        try:
            from app.services import snapshot
            log.info("스냅샷 결과: %s", record_job(db, "snapshot", lambda: snapshot.bake(db)))
        except Exception as e:  # noqa
            log.warning("스냅샷 굽기 실패: %s", e)   # record_job 이 이미 기록·경보함
        if getattr(s, "scheduler_run_backup", False):
            try:
                from scripts.backup import run_backup
                log.info("백업 결과: %s", record_job(db, "backup", run_backup))
            except Exception as e:  # noqa
                log.warning("백업 실패: %s", e)   # record_job 이 이미 기록·경보함


def main(argv=None) -> int:
    import sys as _sys
    argv = argv if argv is not None else _sys.argv[1:]
    init_db()
    if "--once" in argv:            # 크론(Cron Job)용: 1사이클 실행 후 종료
        log.info("단발 실행(--once) — 수집+지오코딩 1사이클")
        _cycle()
        return 0
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
