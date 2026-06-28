"""공시가격 CSV 보강 실행: python -m scripts.import_gongsi --path /path/to/공동주택가격.csv

CSV 는 국토교통부 '공동주택 공시가격' 공식 데이터(가능하면 충북/청주로 필터)를 사용.
미존재 시 건너뜀. 매칭 실패 단지는 보강하지 않음(null 유지).
"""
import argparse
from app.db.session import SessionLocal, init_db
from app.services.gongsi import import_from_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="공동주택 공시가격 CSV 경로")
    args = ap.parse_args()
    init_db()
    db = SessionLocal()
    try:
        print("공시가격 보강:", import_from_csv(db, args.path))
    finally:
        db.close()


if __name__ == "__main__":
    main()
