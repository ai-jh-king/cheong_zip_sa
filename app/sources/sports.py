"""체육시설 커넥터 — '전국체육시설/공공시설개방정보표준데이터'(공공데이터포털).

데이터: 체육관·수영장·풋살장·테니스장 등. 다수 표준데이터가 WGS84 위도·경도 포함 + 일부 사용료.
청주만 필터해 Place(subcategory="sports")로 정규화. 종목/유형은 course/attrs에.

⚠️ 엔드포인트·필드는 Swagger로 확정. tolerant 매핑이라 흔한 이름은 흡수, 못 찾으면 None(왜곡 방지).
키 없으면 0건(안전).
"""
from __future__ import annotations
import logging

from app.core.config import get_settings
from app.sources.places_common import pick, to_float, to_int, lawd_of, is_cheongju, fetch_pages

logger = logging.getLogger(__name__)

SPORTS_URL = "https://api.odcloud.kr/api/15013117/v1/uddi:sports"  # ← 확인 필요(공공시설개방/체육시설 실제 경로)

F = {
    "name":    ["개방시설명", "시설명", "fcltyNm", "체육시설명", "FACLT_NM", "개방장소명"],
    "type":    ["개방시설유형구분", "시설유형", "업종명", "종목명", "FCLTY_TY_NM", "가능종목"],
    "address": ["소재지도로명주소", "도로명주소", "rdnmadr", "ROAD_NM_ADDR", "소재지지번주소"],
    "sigungu": ["시군구명", "시군명", "SIGNGU_NM"],
    "dong":    ["법정동명", "행정동명", "EMD_NM"],
    "lat":     ["위도", "lat", "latitude", "LA", "yCrdnt"],
    "lng":     ["경도", "lng", "longitude", "LO", "xCrdnt"],
    "fee":     ["사용료", "이용요금", "USE_FEE", "사용료금액"],
    "capacity":["수용가능인원수", "수용인원", "정원", "RECPTN_NMPR"],
    "phone":   ["사용안내전화번호", "전화번호", "연락처", "TELNO"],
    "hours":   ["평일운영시작시각", "운영시간", "OPER_TIME"],
}


def _normalize(row: dict) -> dict | None:
    name = pick(row, F["name"])
    if not name:
        return None
    addr = pick(row, F["address"])
    sigungu = pick(row, F["sigungu"])
    if not is_cheongju(addr, sigungu):
        return None
    lawd = lawd_of(addr, sigungu)
    typ = pick(row, F["type"])
    lat, lng = to_float(pick(row, F["lat"])), to_float(pick(row, F["lng"]))
    src_key = f"gov_sports:{name}|{addr or ''}".strip()[:160]
    return {
        "name": str(name)[:150], "category": "sports", "subcategory": "sports",
        "course": typ and str(typ)[:150],
        "road_address": addr and str(addr)[:200], "lawd_cd": lawd,
        "dong_name": (pick(row, F["dong"]) or None) and str(pick(row, F["dong"]))[:40],
        "lat": lat, "lng": lng,
        "tuition": to_int(pick(row, F["fee"])),          # 사용료(공개분)
        "status": None,
        "attrs": {"type": typ, "capacity": to_int(pick(row, F["capacity"])),
                  "phone": pick(row, F["phone"]), "hours": pick(row, F["hours"])},
        "source": "public", "source_dataset": "gov_sports", "source_key": src_key,
    }


def fetch_sports() -> list[dict]:
    s = get_settings()
    key = getattr(s, "academy_service_key", "") or getattr(s, "molit_service_key", "")
    url = getattr(s, "places_sports_url", "") or ""
    if not url:
        logger.warning("체육시설: places_sports_url 미설정 → 수집 생략(활용신청 후 실제 uddi URL을 .env에). 왜곡 방지")
        return []
    raw = fetch_pages(url, key)
    out = [n for n in (_normalize(r) for r in raw) if n]
    logger.info("sports: 청주 체육시설 %d건 정규화", len(out))
    return out
