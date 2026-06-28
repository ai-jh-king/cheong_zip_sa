"""통근시간 사전계산 배치 — (활성 목적지 × 좌표 있는 단지 × 수단) → CommuteTime upsert.

사용:
  python -m scripts.compute_commute                 # car 모드, 신선한 캐시는 skip
  python -m scripts.compute_commute --mode transit  # 대중교통(추정)
  python -m scripts.compute_commute --force         # TTL 무시하고 전부 재계산

운영 메모:
  - car + KAKAO_REST_API_KEY 있으면 길찾기 실측('api'), 아니면 직선거리 추정('haversine').
  - 길찾기 호출은 쿼터/요금이 있으니 증분(신선 캐시 skip) + 단지 좌표 필요(scripts.geocode 선행).
  - 대량이면 운영에서 호출 간 sleep/배치 분할 권장.
"""
from __future__ import annotations
import sys
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.core.config import get_settings
from app.models import Complex, CommuteDestination, CommuteTime
from app.services.commute import compute_one

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("compute_commute")


def run(mode: str = "car", force: bool = False) -> dict:
    init_db()
    s = get_settings()
    ttl = timedelta(days=s.commute_cache_ttl_days)
    now = datetime.utcnow()
    computed = skipped = 0
    with SessionLocal() as db:
        dests = db.scalars(select(CommuteDestination).where(
            CommuteDestination.is_active.is_(True),
            CommuteDestination.lat.isnot(None), CommuteDestination.lng.isnot(None))).all()
        complexes = db.scalars(select(Complex).where(
            Complex.lat.isnot(None), Complex.lng.isnot(None))).all()
        existing = {(c.complex_id, c.destination_id, c.mode): c for c in db.scalars(
            select(CommuteTime).where(CommuteTime.mode == mode)).all()}

        for dest in dests:
            for cx in complexes:
                key = (cx.id, dest.id, mode)
                cur = existing.get(key)
                if cur and not force and cur.computed_at and (now - cur.computed_at) < ttl:
                    skipped += 1
                    continue
                r = compute_one(cx.lat, cx.lng, dest.lat, dest.lng, mode)
                if cur:
                    cur.minutes, cur.distance_m = r["minutes"], r["distance_m"]
                    cur.method, cur.source, cur.computed_at = r["method"], r["source"], now
                else:
                    db.add(CommuteTime(
                        complex_id=cx.id, destination_id=dest.id, mode=mode,
                        minutes=r["minutes"], distance_m=r["distance_m"],
                        method=r["method"], source=r["source"], computed_at=now))
                computed += 1
            db.commit()
    logger.info("통근 계산 완료: 계산 %s · skip %s (mode=%s)", computed, skipped, mode)
    return {"computed": computed, "skipped": skipped, "mode": mode}


if __name__ == "__main__":
    mode = "transit" if "--mode" in sys.argv and "transit" in sys.argv else \
           ("walk" if "walk" in sys.argv else "car")
    run(mode=mode, force="--force" in sys.argv)
