"""
청약홈 분양정보 커넥터 (홈 피드용) — 한국부동산원 '청약홈 분양정보 조회 서비스'.
데이터: 공공데이터포털 data id 15098547 (오픈API). 키 = APPLYHOME_SERVICE_KEY(= data.go.kr 키).

⚠️ 응답 필드·엔드포인트 경로는 데이터셋 Swagger 로 '반드시' 재확인할 것(MOLIT 와 동일 원칙).
   아래는 청약홈 오픈API 통상값이나, 기관/버전에 따라 다를 수 있어 실패 시 None 반환(→ 예시 폴백).
   필드는 tolerant 매핑으로 흡수하고, 못 찾으면 None(왜곡 방지).
"""
from __future__ import annotations
import logging
from datetime import date, datetime

import httpx

from app.core.config import get_settings
from app.core.cache import ttl_cached

logger = logging.getLogger(__name__)

# 청약홈 분양정보(APT) 통상 엔드포인트 — Swagger 확인 후 필요 시 수정.
APPLYHOME_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

# tolerant 필드 후보 (Swagger 확인 후 보강)
F = {
    "notice_no": ["PBLANC_NO", "공고번호", "PBLANC_NM"],
    "name": ["HOUSE_NM", "주택명", "BSNS_MBY_NM"],
    "region": ["SUBSCRPT_AREA_CODE_NM", "공급지역명", "SIDO"],
    "location": ["HSSPLY_ADRES", "공급위치", "ADRES"],
    "notice_date": ["RCRIT_PBLANC_DE", "모집공고일"],
    "begin": ["RCEPT_BGNDE", "청약접수시작일", "GNRL_RNK1_CRSPAREA_RCPTDE_PD"],
    "end": ["RCEPT_ENDDE", "청약접수종료일"],
    "units": ["TOT_SUPLY_HSHLDCO", "공급규모", "총공급세대수"],
    "price_max": ["LTTOT_TOP_AMOUNT", "분양최고금액", "SUPLY_AMOUNT"],
    "url": ["PBLANC_URL", "HMPG_ADRES"],
}


def _pick(row: dict, keys: list[str]):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return None


def _status(begin, end) -> str:
    today = date.today().isoformat()
    if begin and today < str(begin):
        return "접수예정"
    if end and str(begin or "") <= today <= str(end):
        return "접수중"
    if end and today > str(end):
        return "마감"
    return "공고"


def _is_cheongju(region, location) -> bool:
    blob = f"{region or ''} {location or ''}"
    return ("청주" in blob) or ("충북" in blob) or ("충청북도" in blob)


@ttl_cached("cache_ttl_subs_sec", 1800)
def fetch_subscriptions(limit: int = 10) -> list[dict] | None:
    s = get_settings()
    # 청약홈도 data.go.kr → 계정 키 1개 공통. 별도 키 없으면 MOLIT(=data.go.kr) 키 재사용.
    key = s.applyhome_service_key or s.molit_service_key
    if not key:
        return None
    try:
        r = httpx.get(s.applyhome_url or APPLYHOME_URL,
                      params={"serviceKey": key, "page": 1,
                              "perPage": 100, "returnType": "JSON"},
                      timeout=12)
        if r.status_code != 200:
            logger.warning("청약홈 %s: %s", r.status_code, r.text[:120])
            return None
        rows = r.json().get("data") or r.json().get("response", {}).get("body", {}).get("items", [])
        out = []
        for row in rows:
            region = _pick(row, F["region"]); location = _pick(row, F["location"])
            if not _is_cheongju(region, location):
                continue
            begin = _pick(row, F["begin"]); end = _pick(row, F["end"])
            price_max = _pick(row, F["price_max"])
            out.append({
                "notice_no": _pick(row, F["notice_no"]),
                "name": _pick(row, F["name"]) or "(주택명 미상)",
                "location": location or region or "충북",
                "period": f"{begin or '-'} ~ {end or '-'}",
                "begin": begin, "end": end,
                "units": _pick(row, F["units"]),
                "price": (f"최고 {price_max}" if price_max else None),
                "competition_range": None,   # 경쟁률(주택형별 API 연동 시 채움)
                "min_score": None,           # 최저 당첨가점
                "house_types": None,         # 주택형별 상세(분양가·세대·경쟁률·가점)
                "status": _status(begin, end),
                "url": _pick(row, F["url"]),
                "is_sample": False,
            })
        # 최신 공고 우선
        out.sort(key=lambda x: x["period"], reverse=True)
        return out[:limit] or None
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning("청약홈 호출 실패: %s", e)
        return None


# ---------------- 경쟁률·당첨가점·주택형별 분양가 (보강) ----------------
# 청약홈 '경쟁률/당첨 정보' 오픈API. 정확한 엔드포인트·필드는 Swagger 확인 필요.
# applyhome_competition_url 설정 시에만 호출(미설정/실패 → None → 주택형 정보는 비표시, 왜곡 방지).
COMP_F = {
    "notice_no": ["PBLANC_NO", "공고번호"],
    "name": ["HOUSE_NM", "주택명"],
    "house_type": ["HOUSE_TY", "주택형", "HOUSE_DTL_SECD_NM"],
    "units": ["SUPLY_HSHLDCO", "공급세대수", "공급호수"],
    "price": ["LTTOT_TOP_AMOUNT", "분양최고금액", "공급금액"],
    "competition": ["CMPET_RATE", "경쟁률", "GENERAL_CMPET_RATE"],
    "min_score": ["LWET_WIN_GAJEOM", "최저당첨가점", "min_score"],
    "avg_score": ["AVRG_WIN_GAJEOM", "평균당첨가점", "avg_score"],
}


def _ratio(v):
    """'12.3:1' / '12.3' / 12.3 → 12.3 (float) 또는 None."""
    if v is None:
        return None
    s = str(v).split(":")[0].strip()
    try:
        return float(s)
    except ValueError:
        return None


@ttl_cached("cache_ttl_subs_sec", 1800)
def fetch_competition() -> dict | None:
    """{공고번호 또는 주택명: [주택형 상세...]}. 미설정/실패 시 None."""
    s = get_settings()
    url = s.applyhome_competition_url
    key = s.applyhome_service_key or s.molit_service_key
    if not url or not key:
        return None
    try:
        r = httpx.get(url, params={"serviceKey": key, "page": 1,
                                   "perPage": 300, "returnType": "JSON"}, timeout=12)
        if r.status_code != 200:
            logger.warning("청약 경쟁률 %s: %s", r.status_code, r.text[:120])
            return None
        body = r.json()
        rows = body.get("data") or body.get("response", {}).get("body", {}).get("items", []) or []
        groups: dict = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            key_g = _pick(row, COMP_F["notice_no"]) or _pick(row, COMP_F["name"])
            if not key_g:
                continue
            groups.setdefault(key_g, []).append({
                "type": _pick(row, COMP_F["house_type"]),
                "units": _pick(row, COMP_F["units"]),
                "price": _pick(row, COMP_F["price"]),
                "competition": _pick(row, COMP_F["competition"]),
                "min_score": _pick(row, COMP_F["min_score"]),
                "avg_score": _pick(row, COMP_F["avg_score"]),
            })
        return groups or None
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning("청약 경쟁률 호출 실패: %s", e)
        return None


def attach_competition(subs: list[dict] | None, groups: dict | None) -> list[dict] | None:
    """분양 공고에 주택형별 상세(경쟁률·가점·분양가)를 병합."""
    if not subs or not groups:
        return subs
    for sub in subs:
        hts = groups.get(sub.get("notice_no")) or groups.get(sub.get("name"))
        if not hts:
            continue
        sub["house_types"] = hts
        comps = [_ratio(h.get("competition")) for h in hts]
        comps = [c for c in comps if c is not None]
        scores = [_ratio(h.get("min_score")) for h in hts]
        scores = [c for c in scores if c is not None]
        if comps:
            sub["competition_range"] = [min(comps), max(comps)]
        if scores:
            sub["min_score"] = min(scores)
    return subs
