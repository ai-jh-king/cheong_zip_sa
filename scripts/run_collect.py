"""
수집 실행 CLI.

사용법:
  python -m scripts.run_collect init            # DB 테이블 생성
  python -m scripts.run_collect fixtures        # 모의데이터 적재(키 없이 검증)
  python -m scripts.run_collect live            # 실제 국토부 API 수집(키 필요)
  python -m scripts.run_collect live --months 6
"""
import sys
import logging

from app.core.config import get_settings
from app.db.session import init_db, SessionLocal
from app.pipeline.collect import collect_live, collect_from_fixtures
from app.sources.molit.client import MolitKeyMissingError

logging.basicConfig(level=get_settings().log_level,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "help"

    if cmd == "init":
        init_db()
        print("DB 초기화 완료.")
        return 0

    if cmd == "fixtures":
        init_db()
        with SessionLocal() as db:
            res = collect_from_fixtures(db)
        print("모의데이터 적재:", res)
        return 0

    if cmd == "live":
        months = None
        if "--months" in argv:
            months = int(argv[argv.index("--months") + 1])
        init_db()
        try:
            with SessionLocal() as db:
                res = collect_live(db, months_back=months)
            print("실수집 완료:", res)
            return 0
        except MolitKeyMissingError as e:
            print("실패:", e)
            print("→ .env 에 MOLIT_SERVICE_KEY 를 넣거나, 'fixtures' 로 먼저 검증하세요.")
            return 1

    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
