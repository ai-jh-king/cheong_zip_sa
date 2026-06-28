"""단지 기본정보 보강 실행: python -m scripts.enrich [--limit N]"""
import argparse
from app.db.session import SessionLocal, init_db
from app.services.enrich import enrich_complexes, EnrichDisabled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    init_db()
    db = SessionLocal()
    try:
        res = enrich_complexes(db, limit=args.limit or None)
        print("보강 완료:", res)
    except EnrichDisabled as e:
        print("건너뜀:", e)
    finally:
        db.close()


if __name__ == "__main__":
    main()
