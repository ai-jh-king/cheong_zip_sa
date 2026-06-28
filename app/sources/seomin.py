"""
서민금융진흥원 '서민금융 한눈에' 대출상품 커넥터 (공공데이터포털).

근거: 금융위원회_서민금융상품기본정보(data.go.kr/data/15094787) — 취급기관별 서민금융
      대출상품의 명칭·금리·한도·지원대상·상환방식·취급기관 제공. 인증키는 data.go.kr 키 공통.

⚠️ 정확한 엔드포인트 경로·필드명은 해당 데이터셋 명세(Swagger/odcloud)로 '반드시' 확정해야 함.
   본 커넥터는 검증된 URL(SEOMIN_API_URL)이 설정돼 있을 때만 호출하고,
   미설정·실패 시 None → loan.estimate 가 자동 폴백(추가 안 함). (가짜 실데이터 금지 = 왜곡 방지.)

정규화: 행마다 상품 1건. 금리 후보 필드에서 최저~최고 추출, 없으면 그 행은 제외(지어내지 않음).
한도 단위가 모호하면 한도는 None으로 두고 지원대상/한도 텍스트는 req에 담는다.
"""
from __future__ import annotations
import logging

import httpx

from app.core.config import get_settings
from app.core.cache import ttl_cached

logger = logging.getLogger(__name__)

NAME_FIELDS = ["fncPrdNm", "prdNm", "상품명", "금융상품명", "productName"]
INST_FIELDS = ["instNm", "취급기관", "기관명", "취급기관명", "company"]
RATE_FIELDS = ["intRate", "rate", "금리", "대출금리", "lendRate", "irt",
               "minIntRate", "maxIntRate", "최저금리", "최고금리"]
LIMIT_FIELDS = ["limit", "한도", "대출한도", "loanLimit"]
TARGET_FIELDS = ["trgt", "지원대상", "대상", "이용대상", "target"]


def _nums(s) -> list[float]:
    """문자열/숫자에서 % 금리 후보를 추출(예: '3.5~9.9%' → [3.5, 9.9])."""
    if s is None:
        return []
    out = []
    cur = ""
    for ch in str(s):
        if ch.isdigit() or ch == ".":
            cur += ch
        else:
            if cur:
                try:
                    out.append(float(cur))
                except ValueError:
                    pass
            cur = ""
    if cur:
        try:
            out.append(float(cur))
        except ValueError:
            pass
    # 비현실적 값(>30%)은 금리가 아닐 가능성 → 거른다
    return [x for x in out if 0 < x <= 30]


def _first(row: dict, fields: list[str]):
    for f in fields:
        v = row.get(f)
        if v not in (None, ""):
            return v
    return None


def _rows_from(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    for key in ("data", "items", "list", "result"):
        v = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            inner = v.get("item") or v.get("items")
            if isinstance(inner, list):
                return inner
    body = (payload.get("response", {}).get("body", {}) if isinstance(payload, dict) else {})
    items = body.get("items")
    if isinstance(items, dict):
        items = items.get("item")
    return items if isinstance(items, list) else []


@ttl_cached("cache_ttl_loan_sec", 21600)
def fetch_seomin_products(limit: int = 8) -> list[dict] | None:
    """서민금융 대출상품(실연동). 검증된 엔드포인트 미설정/실패 시 None."""
    s = get_settings()
    url = s.seomin_api_url
    key = s.seomin_api_key or s.molit_service_key
    if not url or not key:
        return None
    try:
        r = httpx.get(url, params={"serviceKey": key, "returnType": "JSON",
                                   "page": 1, "perPage": 100}, timeout=12)
        if r.status_code != 200:
            logger.warning("서민금융 %s: %s", r.status_code, r.text[:120])
            return None
        out = []
        for row in _rows_from(r.json()):
            if not isinstance(row, dict):
                continue
            rates = _nums(_first(row, RATE_FIELDS))
            # min/max 별도 필드도 합산
            rates += _nums(row.get("minIntRate")) + _nums(row.get("maxIntRate"))
            if not rates:
                continue
            name = _first(row, NAME_FIELDS) or "서민금융 상품"
            inst = _first(row, INST_FIELDS)
            target = _first(row, TARGET_FIELDS)
            out.append({
                "id": f"seomin_{len(out)}",
                "name": f"{inst} {name}".strip() if inst else str(name),
                "kind": "서민금융",
                "rate_min": round(min(rates), 2),
                "rate_max": round(max(rates), 2),
                "method": "-",
                "limit": None,
                "req": str(target) if target else "자격요건 확인",
                "as_of": None,
                "is_sample": False,
            })
        if not out:
            return None
        out.sort(key=lambda p: p["rate_min"])
        return out[:limit]
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning("서민금융 호출 실패: %s", e)
        return None
