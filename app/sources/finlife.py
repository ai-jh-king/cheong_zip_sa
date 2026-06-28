"""
finlife(금융감독원 '금융상품 한눈에') 대출 금리 커넥터.

대상: 주택담보대출 / 전세자금대출 — 은행권(topFinGrpNo=020000).
응답 구조: result.baseList(상품기본) + result.optionList(금리옵션), fin_prdt_cd 로 조인.
  baseList:   fin_co_no, kor_co_nm, fin_prdt_cd, fin_prdt_nm, loan_lmt, dcls_strt_day ...
  optionList: fin_prdt_cd, lend_rate_type_nm(고정/변동), lend_rate_min, lend_rate_max, rpay_type_nm ...
⚠️ 필드명은 finlife 오픈API 명세 기준값. 실패/키없음 시 None 반환 → loan.estimate 가 예시표로 폴백.

키: FINLIFE_API_KEY (finlife.fss.or.kr 인증키). 금액 단위는 만원으로 환산해 반환.
"""
from __future__ import annotations
import logging

import httpx

from app.core.config import get_settings
from app.core.cache import ttl_cached

logger = logging.getLogger(__name__)
BASE = "https://finlife.fss.or.kr/finlifeapi"   # http는 307 리다이렉트 → https 직접 호출
MORTGAGE = f"{BASE}/mortgageLoanProductsSearch.json"
RENT = f"{BASE}/rentHouseLoanProductsSearch.json"
BANK = "020000"  # 은행


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fetch(url: str, key: str) -> tuple[list, list] | None:
    r = httpx.get(url, params={"auth": key, "topFinGrpNo": BANK, "pageNo": 1},
                  timeout=12, follow_redirects=True)   # http→https 307 대응
    if r.status_code != 200:
        logger.warning("finlife HTTP %s: %s", r.status_code, r.text[:120])
        return None
    result = r.json().get("result", {})
    err = result.get("err_cd")
    if err and err != "000":   # 키 미승인/오류 시 200이라도 빈 응답 → 원인 로그
        logger.warning("finlife err_cd=%s msg=%s", err, result.get("err_msg"))
        return None
    return result.get("baseList", []) or [], result.get("optionList", []) or []


def _products(url: str, key: str, kind_label: str, limit: int) -> list[dict]:
    pair = _fetch(url, key)
    if not pair:
        return []
    base, opts = pair
    by_prdt: dict[str, list] = {}
    for o in opts:
        by_prdt.setdefault(o.get("fin_prdt_cd"), []).append(o)
    out = []
    for b in base:
        os = by_prdt.get(b.get("fin_prdt_cd"), [])
        mins = [_num(o.get("lend_rate_min")) for o in os if _num(o.get("lend_rate_min")) is not None]
        maxs = [_num(o.get("lend_rate_max")) for o in os if _num(o.get("lend_rate_max")) is not None]
        if not mins:
            continue
        methods = sorted({o.get("rpay_type_nm") for o in os if o.get("rpay_type_nm")})
        out.append({
            "id": f"{b.get('fin_co_no')}_{b.get('fin_prdt_cd')}",
            "name": f"{b.get('kor_co_nm','')} {b.get('fin_prdt_nm','')}".strip(),
            "kind": kind_label,
            "rate_min": round(min(mins), 2),
            "rate_max": round(max(maxs), 2) if maxs else round(min(mins), 2),
            "method": "/".join(methods) if methods else "-",
            "limit": None,           # 한도는 상품별 텍스트가 많아 표기 보류(왜곡 방지)
            "req": "은행 심사",
            "as_of": b.get("dcls_strt_day"),
            "is_sample": False,
        })
    out.sort(key=lambda p: p["rate_min"])
    return out[:limit]


@ttl_cached("cache_ttl_loan_sec", 21600)
def fetch_loan_products(limit: int = 10) -> list[dict] | None:
    """은행 주담대 + 전세자금대출 실금리 상품. 키 없거나 실패 시 None."""
    s = get_settings()
    if not s.finlife_api_key:
        return None
    try:
        base = s.finlife_base_url or BASE
        mort = _products(f"{base}/mortgageLoanProductsSearch.json", s.finlife_api_key, "은행 주담대", limit)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning("finlife 주담대 실패: %s", e)
        mort = []
    try:
        rent = _products(f"{base}/rentHouseLoanProductsSearch.json", s.finlife_api_key, "은행 전세", limit)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning("finlife 전세 실패: %s", e)
        rent = []
    prods = (mort or []) + (rent or [])
    if not prods:
        return None
    prods.sort(key=lambda p: p["rate_min"])
    return prods[:limit]
