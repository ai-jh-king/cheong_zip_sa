"""
단지 지오코딩 실행 (지도 핀 좌표 캐싱).

사용법:
  python -m scripts.geocode            # 거래에 등장한 단지 전체 지오코딩
  python -m scripts.geocode --limit 50 # 일부만(쿼터 절약/테스트)

필요: .env 에 KAKAO_REST_API_KEY. 결과는 Complex.lat/lng 에 저장돼 지도에 표시됨.
좌표를 못 찾은 단지는 저장하지 않으므로 지도에 임의 위치로 찍히지 않는다(왜곡 방지).
"""
import sys
import logging

from app.core.config import get_settings
from app.db.session import init_db, SessionLocal
from app.services.geocode import run_geocode, GeocodeKeyMissing

logging.basicConfig(level=get_settings().log_level,
                    format="%(asctime)s %(levelname)s: %(message)s")


def main(argv) -> int:
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    init_db()
    try:
        with SessionLocal() as db:
            res = run_geocode(db, limit=limit)
        print("지오코딩 완료:", res)
        return 0
    except GeocodeKeyMissing as e:
        print("실패:", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
