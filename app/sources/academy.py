"""학원·교습소 커넥터 — NEIS 교육정보 개방포털 '학원교습소정보'(acaInsTiInfo).

⚠️ 데이터 출처 정정: data.go.kr '전국학원및교습소표준데이터'(15096277)는 CSV 파일 제공이고,
   실제 Open API 는 **NEIS(open.neis.go.kr)** 에서 제공한다. 따라서 여기서는 NEIS acaInsTiInfo 를 사용.
   - 키: NEIS 에서 별도 발급(KEY). data.go.kr/MOLIT 키와 다름 → ACADEMY_SERVICE_KEY 에 NEIS 키를 넣을 것.
   - 시도교육청코드(ATPT_OFCDC_SC_CODE)로 충북(M10)만 요청 → 효율적. 이후 청주만 필터.
   - 전국 확장: OFFICE_CODES 에 다른 교육청 코드를 추가하면 됨(지금은 충북 M10).
응답/필드는 NEIS 명세 기준(아래 F). 키 없으면 0건(안전).
"""
from __future__ import annotations
import logging

import httpx

from app.core.config import get_settings
from app.services.places import classify_academy
from app.sources.places_common import to_int, to_float, lawd_of, is_cheongju

logger = logging.getLogger(__name__)

ACADEMY_URL = "https://open.neis.go.kr/hub/acaInsTiInfo"   # NEIS 학원교습소정보(실 제공 API)
OFFICE_CODES = ["M10"]   # 충청북도교육청. 전국 확장 시 다른 시도교육청 코드 추가.

# NEIS acaInsTiInfo 실제 필드명 우선 + 호환 후보
F = {
    "name":    ["ACA_NM", "학원명"],
    "field":   ["REALM_SC_NM", "분야명"],
    "series":  ["LE_ORD_NM", "교습계열명"],
    "course":  ["LE_CRSE_NM", "교습과정명"],
    "address": ["FA_RDNMA", "도로명주소"],
    "dong":    ["ADMST_ZONE_NM", "행정구역명"],
    "capacity":["TOFOR_SMTOT", "정원"],
    "status":  ["ACA_ASNUM", "등록상태"],   # 등록상태 코드/일자 계열(있으면)
}


def _pick(row: dict, keys: list[str]):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return None


def _normalize(row: dict) -> dict | None:
    name = _pick(row, F["name"])
    if not name:
        return None
    addr = _pick(row, F["address"])
    dong = _pick(row, F["dong"])
    if not is_cheongju(addr, dong):        # 충북 내 청주만
        return None
    field = _pick(row, F["field"])
    series = _pick(row, F["series"])
    course = _pick(row, F["course"])
    sub = classify_academy(f"{field or ''} {series or ''}", course)
    return {
        "name": str(name)[:150], "category": "education", "subcategory": sub,
        "course": (course or series or field or None) and str(course or series or field)[:150],
        "road_address": addr and str(addr)[:200], "lawd_cd": lawd_of(addr, dong),
        "dong_name": (dong or None) and str(dong)[:40],
        "lat": None, "lng": None,           # NEIS 는 좌표 미제공 → scripts.geocode 로 보강
        "tuition": None,
        "status": (_pick(row, F["status"]) or None) and str(_pick(row, F["status"]))[:20],
        "attrs": {"capacity": to_int(_pick(row, F["capacity"])), "field": field, "series": series},
        "source": "public", "source_dataset": "neis_academy",
        "source_key": f"neis_academy:{name}|{addr or ''}".strip()[:160],
    }


def fetch_academies(limit_pages: int = 50, per_page: int = 1000) -> list[dict]:
    """충북교육청(M10) 학원·교습소 → 청주만 Place dict. NEIS 키 없으면 빈 리스트."""
    s = get_settings()
    key = getattr(s, "academy_service_key", "")   # NEIS 키
    if not key:
        logger.warning("academy(NEIS): ACADEMY_SERVICE_KEY(NEIS 키) 없음 → 수집 생략")
        return []
    out: list[dict] = []
    try:
        with httpx.Client(timeout=20) as client:
            for office in OFFICE_CODES:
                for page in range(1, limit_pages + 1):
                    params = {"KEY": key, "Type": "json", "pIndex": page, "pSize": per_page,
                              "ATPT_OFCDC_SC_CODE": office}
                    r = client.get(ACADEMY_URL, params=params)
                    if r.status_code != 200:
                        logger.warning("academy(NEIS): HTTP %s (office %s p%s)", r.status_code, office, page)
                        break
                    data = r.json()
                    # NEIS 구조: {"acaInsTiInfo":[{"head":...},{"row":[...]}]}
                    blocks = data.get("acaInsTiInfo")
                    if not blocks or len(blocks) < 2:
                        break
                    rows = blocks[1].get("row") or []
                    if not rows:
                        break
                    for row in rows:
                        n = _normalize(row)
                        if n:
                            out.append(n)
                    if len(rows) < per_page:
                        break
    except Exception as e:
        logger.warning("academy(NEIS): 수집 오류 %s", e)
    logger.info("academy(NEIS): 청주 학원 %d건 정규화", len(out))
    return out
