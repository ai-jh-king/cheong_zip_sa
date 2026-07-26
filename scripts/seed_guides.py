"""집사 도감 — 첫 시리즈 시드(멱등). 편은 admin API 로 발행(주 1편 큐레이션).

사용:
  python -m scripts.seed_guides
"""
import logging

from app.db.session import init_db, SessionLocal
from app.models import GuideSeries

logging.basicConfig(level="INFO", format="%(levelname)s: %(message)s")
log = logging.getLogger("seed_guides")

SERIES = [
    dict(key="cheongju", name="집사가 알려주는 청주",
         description="청주에서 잘 살고 싶은 사람을 위한 청집사의 실사용 안내서",
         cover_emoji="🏘", sort_order=1),
    # 후속 시리즈(계약/대출/안전/이사/청약)는 콘텐츠가 준비될 때 추가.
]


def run() -> dict:
    init_db()
    created = 0
    with SessionLocal() as db:
        for s in SERIES:
            if db.get(GuideSeries, s["key"]):
                continue
            db.add(GuideSeries(**s))
            created += 1
        db.commit()
    return {"created": created, "total": len(SERIES)}


if __name__ == "__main__":
    log.info("결과: %s", run())
