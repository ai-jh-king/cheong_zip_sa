"""의료기관 커넥터 — '전국의료기관표준데이터'(공공데이터포털, data 15096293).

⚠️ 좌표계 주의: 이 표준데이터는 **Bessel 중부원점TM(EPSG:5174)**.
   - WGS84 위경도 필드가 있으면 우선 사용.
   - 없으면 TM(X/Y) → WGS84 변환(pyproj). 변환 불가/범위 밖이면 좌표 None(틀린 좌표 저장 금지 — 왜곡 방지).
청주만 필터. 종별 → subcategory(병원·의원=hospital, 약국=pharmacy). 키 없으면 0건(안전).
"""
from __future__ import annotations
import logging

from app.core.config import get_settings
from app.sources.places_common import (
    pick, to_float, to_int, lawd_of, is_cheongju, fetch_pages, wgs84_from_tm5174,
)

logger = logging.getLogger(__name__)

MEDICAL_URL = "https://api.odcloud.kr/api/15096293/v1/uddi:medical"  # ← 확인 필요(실제 경로)

F = {
    "name":    ["기관명", "요양기관명", "병원명", "의료기관명", "dutyName", "yadmNm", "HSPTL_NM"],
    "type":    ["종별", "종별명", "의료기관종별명", "clCdNm", "MDX_DIV_NM"],
    "address": ["소재지도로명주소", "도로명주소", "dutyAddr", "rdnmadr", "ROAD_NM_ADDR"],
    "sigungu": ["시군구명", "SIGNGU_NM"],
    "dong":    ["법정동명", "행정동명", "EMD_NM"],
    "lat":     ["위도", "WGS84위도", "lat", "latitude", "YPos"],   # WGS84(있으면 우선)
    "lng":     ["경도", "WGS84경도", "lng", "longitude", "XPos"],
    "tm_x":    ["X좌표", "좌표정보(X)", "xCrdnt", "posX", "X_CRDNT"],   # EPSG:5174
    "tm_y":    ["Y좌표", "좌표정보(Y)", "yCrdnt", "posY", "Y_CRDNT"],
    "phone":   ["전화번호", "대표전화", "dutyTel1", "TELNO"],
    "beds":    ["병상수", "허가병상수", "TOT_BED_CNT"],
}


def _subcat(name: str | None, typ: str | None) -> str:
    t = f"{name or ''} {typ or ''}"
    if "약국" in t:
        return "pharmacy"
    return "hospital"


def _coords(row: dict):
    """WGS84 필드 우선 → 없으면 TM5174 변환. (lat, lng) 또는 (None, None)."""
    lat, lng = to_float(pick(row, F["lat"])), to_float(pick(row, F["lng"]))
    if lat is not None and lng is not None and 33.0 < lat < 39.0 and 124.0 < lng < 132.0:
        return lat, lng
    # WGS84 없거나 범위 밖 → TM 변환 시도
    return wgs84_from_tm5174(pick(row, F["tm_x"]), pick(row, F["tm_y"]))


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
    lat, lng = _coords(row)
    src_key = f"gov_medical:{name}|{addr or ''}".strip()[:160]
    return {
        "name": str(name)[:150], "category": "living", "subcategory": _subcat(name, typ),
        "course": typ and str(typ)[:150],
        "road_address": addr and str(addr)[:200], "lawd_cd": lawd,
        "dong_name": (pick(row, F["dong"]) or None) and str(pick(row, F["dong"]))[:40],
        "lat": lat, "lng": lng,
        "tuition": None,
        "status": None,
        "attrs": {"type": typ, "beds": to_int(pick(row, F["beds"])), "phone": pick(row, F["phone"])},
        "source": "public", "source_dataset": "gov_medical", "source_key": src_key,
    }


def fetch_medical() -> list[dict]:
    s = get_settings()
    key = getattr(s, "academy_service_key", "") or getattr(s, "molit_service_key", "")
    raw = fetch_pages(MEDICAL_URL, key)
    out = [n for n in (_normalize(r) for r in raw) if n]
    logger.info("medical: 청주 의료기관 %d건 정규화", len(out))
    return out
