"""어린이집·유치원 커넥터 — 어린이집정보/유치원알리미 표준데이터(공공데이터포털).

청주만 필터해 Place(subcategory="daycare")로 정규화. 정원·현원은 attrs.
좌표 없으면 None(거리/지도 제외, 목록 노출). 키 없으면 0건(안전). ⚠️ URL·필드 Swagger 확정.
"""
from __future__ import annotations
import logging

from app.core.config import get_settings
from app.sources.places_common import pick, to_int, to_float, lawd_of, is_cheongju, fetch_pages

logger = logging.getLogger(__name__)

DAYCARE_URL = "https://api.odcloud.kr/api/15059593/v1/uddi:daycare"  # ← 확인 필요(어린이집 표준데이터)

F = {
    "name":    ["어린이집명", "유치원명", "crname", "fcltyNm", "CRNAME"],
    "type":    ["어린이집유형구분", "유형", "crtypeNm", "설립유형", "CRTYPE_NM"],
    "address": ["주소", "도로명주소", "소재지도로명주소", "craddr", "ROAD_NM_ADDR"],
    "sigungu": ["시군구명", "SIGNGU_NM"],
    "dong":    ["법정동명", "행정동명", "EMD_NM"],
    "lat":     ["위도", "la", "lat", "latitude", "LA"],
    "lng":     ["경도", "lo", "lng", "longitude", "LO"],
    "capacity":["정원", "crcapat", "정원수", "CRCAPAT"],
    "current": ["현원", "crchcnt", "현원수", "CRCHCNT"],
    "phone":   ["전화번호", "crtelno", "TELNO"],
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
        "name": str(name)[:150], "category": "living", "subcategory": "daycare",
        "course": typ and str(typ)[:150],
        "road_address": addr and str(addr)[:200], "lawd_cd": lawd_of(addr, sigungu),
        "dong_name": (pick(row, F["dong"]) or None) and str(pick(row, F["dong"]))[:40],
        "lat": to_float(pick(row, F["lat"])), "lng": to_float(pick(row, F["lng"])),
        "tuition": None, "status": None,
        "attrs": {"type": typ, "capacity": to_int(pick(row, F["capacity"])),
                  "current": to_int(pick(row, F["current"])), "phone": pick(row, F["phone"])},
        "source": "public", "source_dataset": "gov_daycare",
        "source_key": f"gov_daycare:{name}|{addr or ''}".strip()[:160],
    }


def fetch_daycares() -> list[dict]:
    s = get_settings()
    key = getattr(s, "academy_service_key", "") or getattr(s, "molit_service_key", "")
    raw = fetch_pages(DAYCARE_URL, key)
    out = [n for n in (_normalize(r) for r in raw) if n]
    logger.info("daycare: 청주 어린이집·유치원 %d건 정규화", len(out))
    return out
