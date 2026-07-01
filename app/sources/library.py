"""도서관 커넥터 — '전국도서관표준데이터'(공공데이터포털, data 15013109).

WGS84 위도·경도 포함. 청주만 필터해 Place(subcategory="library")로 정규화.
운영시간·좌석수는 attrs. 키 없으면 0건(안전). ⚠️ URL·필드는 Swagger로 확정(tolerant 흡수).
"""
from __future__ import annotations
import logging

from app.core.config import get_settings
from app.sources.places_common import pick, to_int, lawd_of, is_cheongju, fetch_pages, to_float

logger = logging.getLogger(__name__)

LIBRARY_URL = "https://api.odcloud.kr/api/15013109/v1/uddi:library"  # ← 확인 필요

F = {
    "name":    ["도서관명", "libNm", "fcltyNm", "LBRRY_NM"],
    "type":    ["도서관유형", "libType", "LBRRY_TY_NM"],
    "address": ["소재지도로명주소", "도로명주소", "rdnmadr", "ROAD_NM_ADDR"],
    "sigungu": ["시군구명", "SIGNGU_NM"],
    "dong":    ["법정동명", "행정동명", "EMD_NM"],
    "lat":     ["위도", "lat", "latitude", "LA"],
    "lng":     ["경도", "lng", "longitude", "LO"],
    "seats":   ["열람좌석수", "좌석수", "RDROOM_SEAT_CO"],
    "hours":   ["평일운영시작시각", "운영시간", "WEEKDAY_OPER_BEGIN_TIME"],
    "phone":   ["도서관전화번호", "전화번호", "TELNO"],
}


def _normalize(row: dict) -> dict | None:
    name = pick(row, F["name"])
    if not name:
        return None
    addr, sigungu = pick(row, F["address"]), pick(row, F["sigungu"])
    if not is_cheongju(addr, sigungu):
        return None
    typ = pick(row, F["type"])
    return {
        "name": str(name)[:150], "category": "living", "subcategory": "library",
        "course": typ and str(typ)[:150],
        "road_address": addr and str(addr)[:200], "lawd_cd": lawd_of(addr, sigungu),
        "dong_name": (pick(row, F["dong"]) or None) and str(pick(row, F["dong"]))[:40],
        "lat": to_float(pick(row, F["lat"])), "lng": to_float(pick(row, F["lng"])),
        "tuition": None, "status": None,
        "attrs": {"type": typ, "seats": to_int(pick(row, F["seats"])),
                  "hours": pick(row, F["hours"]), "phone": pick(row, F["phone"])},
        "source": "public", "source_dataset": "gov_library",
        "source_key": f"gov_library:{name}|{addr or ''}".strip()[:160],
    }


def fetch_libraries() -> list[dict]:
    s = get_settings()
    key = getattr(s, "academy_service_key", "") or getattr(s, "molit_service_key", "")
    raw = fetch_pages(LIBRARY_URL, key)
    out = [n for n in (_normalize(r) for r in raw) if n]
    logger.info("library: 청주 도서관 %d건 정규화", len(out))
    return out
