"""
지오코딩 실행 (지도 핀 좌표 캐싱).

사용법:
  python -m scripts.geocode                  # 거래에 등장한 단지(Complex) 전체 지오코딩
  python -m scripts.geocode --limit 50       # 일부만(쿼터 절약/테스트)
  python -m scripts.geocode places           # 시설(Place) 지오코딩(NEIS 학원 등 좌표 미제공 소스)
  python -m scripts.geocode places --limit 50
  python -m scripts.geocode all              # 단지 + 시설 모두

필요: .env 에 KAKAO_REST_API_KEY(권장). 결과는 lat/lng 에 저장돼 지도에 표시됨.
좌표를 못 찾은 대상은 저장하지 않으므로 지도에 임의 위치로 찍히지 않는다(왜곡 방지).
"""
import sys
import logging

from app.core.config import get_settings
from app.db.session import init_db, SessionLocal
from app.services.geocode import run_geocode, run_geocode_places, GeocodeKeyMissing

logging.basicConfig(level=get_settings().log_level,
                    format="%(asctime)s %(levelname)s: %(message)s")


def main(argv) -> int:
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    cmd = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else "complex"
    init_db()
    try:
        with SessionLocal() as db:
            if cmd == "places":
                res = run_geocode_places(db, limit=limit)
                print("시설 지오코딩 완료:", res)
            elif cmd == "all":
                r1 = run_geocode(db, limit=limit)
                r2 = run_geocode_places(db, limit=limit)
                print("단지:", r1, "/ 시설:", r2)
            else:
                res = run_geocode(db, limit=limit)
                print("단지 지오코딩 완료:", res)
        return 0
    except GeocodeKeyMissing as e:
        print("실패:", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
