"""통근권 목적지 시드 적재.

사용:
  python -m scripts.seed_commute            # 시드 upsert(key 기준, 좌표 seed_approx)
  python -m scripts.seed_commute --geocode  # address 기반 카카오 지오코딩으로 좌표 갱신(키 필요)

멱등: key 가 있으면 갱신, 없으면 생성. 좌표를 운영자가 manual 로 바꿨으면 --geocode 가 덮어쓰지 않음.
"""
from __future__ import annotations
import sys
import logging

from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.models import CommuteDestination
from app.data.commute_seed import COMMUTE_DESTINATIONS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_commute")


def seed(geocode: bool = False) -> int:
    init_db()
    n = 0
    with SessionLocal() as db:
        for d in COMMUTE_DESTINATIONS:
            row = db.scalar(select(CommuteDestination).where(CommuteDestination.key == d["key"]))
            if row is None:
                row = CommuteDestination(
                    key=d["key"], name=d["name"], category=d["category"],
                    lat=d.get("lat"), lng=d.get("lng"), address=d.get("address"),
                    gu=d.get("gu"), sort_order=d.get("sort_order", 100),
                    coord_method="seed_approx", is_active=True,
                )
                db.add(row)
                n += 1
            else:
                # 메타만 갱신(좌표는 manual 이면 보존)
                row.name, row.category = d["name"], d["category"]
                row.address, row.gu = d.get("address"), d.get("gu")
                row.sort_order = d.get("sort_order", 100)
                if row.coord_method in (None, "seed_approx") and row.lat is None:
                    row.lat, row.lng = d.get("lat"), d.get("lng")
                    row.coord_method = "seed_approx"
            if geocode and row.coord_method != "manual" and row.address:
                ll = _geocode(row.address)
                if ll:
                    row.lat, row.lng, row.coord_method = ll[0], ll[1], "geocoded"
        db.commit()
    logger.info("목적지 시드 완료: 신규 %s건 / 전체 %s건", n, len(COMMUTE_DESTINATIONS))
    return n


def _geocode(address: str):
    """카카오 주소 지오코딩(있으면). 실패 시 None."""
    try:
        import httpx
        from app.core.config import get_settings
        s = get_settings()
        if not s.kakao_rest_api_key:
            logger.warning("KAKAO_REST_API_KEY 없음 — 지오코딩 건너뜀")
            return None
        r = httpx.get(s.kakao_address_url, params={"query": address},
                      headers={"Authorization": f"KakaoAK {s.kakao_rest_api_key}"}, timeout=8.0)
        r.raise_for_status()
        docs = r.json().get("documents") or []
        if docs:
            return float(docs[0]["y"]), float(docs[0]["x"])
    except Exception as e:  # noqa: BLE001
        logger.debug("지오코딩 실패(%s): %s", address, e)
    return None


if __name__ == "__main__":
    seed(geocode="--geocode" in sys.argv)
