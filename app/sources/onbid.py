"""한국자산관리공사(캠코) 온비드 공매 물건 커넥터.

배경: 법원 '경매'(courtauction.go.kr)는 공식 Open API 가 없어 연동하지 않는다
      (스크래핑 금지 원칙 — 링크·지식 콘텐츠로만 안내).
      캠코 '공매'는 공공데이터포털(data.go.kr) 공식 API 가 있어 실데이터 연동 대상.
      키는 data.go.kr 공통(MOLIT_SERVICE_KEY) 재사용 — 단, '온비드 공매물건 조회'
      활용신청이 별도로 필요(미신청 시 인증 오류 → None 반환·UI 안내).

⚠️ 오퍼레이션 경로·요청 파라미터·응답 필드는 온비드 API 문서/Swagger 로 확정 필요.
   본 커넥터는 tolerant 후보키 매핑으로 흡수하고, 매핑 실패 필드는 None(왜곡 없음).
   응답은 data.go.kr 표준 XML(<response><body><items><item>…)을 가정하되 JSON 도 흡수.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import httpx

from app.core.cache import ttl_cached
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 캠코 공매물건 목록 조회(문서 공개 기본값) — 운영에서 ONBID_LIST_URL 로 오버라이드 가능
DEFAULT_LIST_URL = ("http://openapi.onbid.co.kr/openapi/services/"
                    "KamcoPblsalThingInquireSvc/getKamcoPbctCltrList")

# 후보 필드 매핑(⚠️ Swagger 확인 후 보강) — 표기 다양성 흡수, 없으면 None
_FIELDS = {
    "name": ["CLTR_NM", "cltrNm"],
    "addr": ["LDNM_ADRS", "NMRD_ADRS", "ldnmAdrs", "nmrdAdrs"],
    "category": ["CTGR_FULL_NM", "ctgrFullNm"],
    "min_bid": ["MIN_BID_PRC", "minBidPrc"],
    "appraisal": ["APSL_ASES_AVG_AMT", "apslAsesAvgAmt"],
    "bid_begin": ["PBCT_BEGN_DTM", "pbctBegnDtm"],
    "bid_end": ["PBCT_CLS_DTM", "pbctClsDtm"],
    "status": ["PBCT_CLTR_STAT_NM", "pbctCltrStatNm"],
    "mgmt_no": ["CLTR_MNMT_NO", "cltrMnmtNo", "CLTR_NO", "cltrNo"],
}


def _pick(d: dict, keys: list[str]):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", "null"):
            return v
    return None


def _to_int(v):
    try:
        return int(float(str(v).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def normalize_item(raw: dict) -> dict:
    """온비드 원시 행 → 표준 행. 숫자 실패·필드 누락은 None(왜곡 없음)."""
    return {
        "name": _pick(raw, _FIELDS["name"]),
        "addr": _pick(raw, _FIELDS["addr"]),
        "category": _pick(raw, _FIELDS["category"]),
        "min_bid": _to_int(_pick(raw, _FIELDS["min_bid"])),           # 최저입찰가(원)
        "appraisal": _to_int(_pick(raw, _FIELDS["appraisal"])),       # 감정가(원)
        "bid_begin": _pick(raw, _FIELDS["bid_begin"]),
        "bid_end": _pick(raw, _FIELDS["bid_end"]),
        "status": _pick(raw, _FIELDS["status"]),
        "mgmt_no": _pick(raw, _FIELDS["mgmt_no"]),
        "source": "ONBID",
    }


def _rows_from_xml(text: str) -> list[dict]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    rows = []
    for it in root.iter("item"):
        rows.append({c.tag: (c.text or "").strip() for c in it})
    return rows


def _rows_from_json(payload) -> list[dict]:
    body = (payload.get("response", {}).get("body", {}) if isinstance(payload, dict) else {})
    items = body.get("items")
    if isinstance(items, dict):
        items = items.get("item")
    if isinstance(items, list):
        return items
    return []


@ttl_cached("cache_ttl_news_sec", 21600)
def fetch_public_sale(region: str = "청주") -> list[dict] | None:
    """온비드 공매 물건(주소에 region 포함만). 미연동·실패 시 None(호출측에서 안내)."""
    s = get_settings()
    url = s.onbid_list_url or DEFAULT_LIST_URL
    key = s.onbid_api_key or s.molit_service_key
    if not key:
        return None
    try:
        r = httpx.get(url, params={"serviceKey": key, "numOfRows": 300, "pageNo": 1}, timeout=15)
        if r.status_code != 200:
            logger.warning("온비드 %s: %s", r.status_code, r.text[:150])
            return None
        text = r.text or ""
        rows = _rows_from_xml(text) if text.lstrip().startswith("<") else _rows_from_json(r.json())
        # data.go.kr 인증 오류(활용신청 전)는 200 + 에러 XML 로 오는 경우가 있음 → 행 0 = None
        if not rows:
            if "SERVICE" in text.upper() or "인증" in text:
                logger.info("온비드 미연동(활용신청 필요 추정): %s", text[:120])
            return None
        out = [normalize_item(x) for x in rows]
        out = [x for x in out if x["name"] and x["addr"] and region in x["addr"]]
        out.sort(key=lambda x: (x["bid_end"] or "9999"))
        return out
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("온비드 호출 실패: %s", e)
        return None
