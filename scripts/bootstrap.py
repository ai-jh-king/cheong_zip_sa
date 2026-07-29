"""빈 DB → 서비스 가능 상태로 한 번에 복구(재해복구·신규 환경 구축 공용).

사용:
  python -m scripts.bootstrap                 # 전체(마이그레이션→시드→수집→지오코딩)
  python -m scripts.bootstrap --no-collect    # 시드까지만(빠른 확인)
  python -m scripts.bootstrap --months 12     # 수집 개월 수 지정

배경: Render 무료 PostgreSQL 만료로 DB가 사라진 실사고(2026-07) — 백업이 임시 파일시스템에
      저장돼 유실. 그때 필요한 절차를 사람 손 없이 순서대로 실행하는 단일 진입점.

각 단계는 멱등(이미 있으면 건너뜀)이며, 하나가 실패해도 나머지는 계속 진행한다
(예: 카카오 키 없으면 지오코딩만 건너뜀 — 수집·시세는 정상).
"""
from __future__ import annotations

import argparse
import logging
import time

logging.basicConfig(level="INFO", format="%(levelname)s: %(message)s")
log = logging.getLogger("bootstrap")


def _step(name: str, fn):
    t0 = time.time()
    try:
        out = fn()
        log.info("✅ %s (%.1fs): %s", name, time.time() - t0, out)
        return {"step": name, "ok": True, "result": out}
    except Exception as e:  # noqa: BLE001 — 한 단계 실패가 전체를 막지 않게
        log.warning("⚠️ %s 실패 (%.1fs): %s", name, time.time() - t0, e)
        return {"step": name, "ok": False, "error": str(e)}


def run(collect: bool = True, months: int | None = None) -> dict:
    results = []

    # 1) 스키마(Alembic) — 운영 스키마 권위 소스
    def _migrate():
        from scripts.db_upgrade import main as db_upgrade
        rc = db_upgrade([])
        if rc:
            raise RuntimeError(f"db_upgrade rc={rc}")
        return "alembic head"
    results.append(_step("마이그레이션", _migrate))

    # 2) 시드(멱등) — 도감·호재·통근거점
    from app.db.session import SessionLocal

    def _seed_guides():
        from scripts.seed_guides import run as r
        return r()
    results.append(_step("도감 시드", _seed_guides))

    def _seed_landmarks():
        from scripts.seed_landmarks import main as m
        return {"rc": m()}
    results.append(_step("개발호재 시드", _seed_landmarks))

    def _seed_commute():
        from scripts.seed_commute import seed
        return {"destinations": seed()}
    results.append(_step("통근거점 시드", _seed_commute))

    # 3) 실거래 수집(키 필요) — 시세·지도·랭킹의 원천
    if collect:
        def _collect():
            from app.pipeline.collect import collect_live
            with SessionLocal() as db:
                return collect_live(db) if months is None else collect_live(db, months_back=months)
        results.append(_step("실거래 수집", _collect))

        # 4) 지오코딩(주소 기반) — 지도 마커. 카카오 키 없으면 자동 건너뜀
        def _geocode():
            from app.services.geocode import run_geocode, GeocodeKeyMissing
            with SessionLocal() as db:
                try:
                    return run_geocode(db)
                except GeocodeKeyMissing:
                    return "키 없음 — 건너뜀"
        results.append(_step("지오코딩", _geocode))

        # 5) 집계 스냅샷 프리컴퓨트(첫 로드 속도)
        def _snapshot():
            from app.services import snapshot
            with SessionLocal() as db:
                return snapshot.bake(db)
        results.append(_step("집계 스냅샷", _snapshot))

    ok = sum(1 for r in results if r["ok"])
    log.info("완료: %s/%s 단계 성공", ok, len(results))
    return {"steps": results, "ok_count": ok, "total": len(results)}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--no-collect", action="store_true", help="수집·지오코딩 생략(시드까지만)")
    p.add_argument("--months", type=int, default=None, help="수집 개월 수(기본 설정값)")
    a = p.parse_args()
    run(collect=not a.no_collect, months=a.months)
