"""
한국주택금융공사(HF) 정책대출 금리 커넥터 — 디딤돌·보금자리론.

근거: HF 오픈API(hf.go.kr/abc/hf-open-api-webpage)에 '보금자리론 대출 금리 조회',
      '디딤돌대출 금리 조회'가 존재하며, 인증키는 공공데이터포털(data.go.kr) 키를 공통 사용.
      → 별도 키 없음. MOLIT_SERVICE_KEY(=data.go.kr 키) 재사용.

⚠️ 정확한 엔드포인트 경로·오퍼레이션명·응답 필드는 HF 오픈API 문서/Swagger로 '반드시' 확정해야 함.
   본 커넥터는 검증된 URL(HF_POLICY_API_URL)이 설정되어 있을 때만 호출하고,
   미설정·실패 시 None 을 반환 → loan.estimate 는 설정값(POLICY_PRODUCTS, 예시)로 폴백.
   (검증 안 된 엔드포인트를 추측해 '가짜 실데이터'를 만들지 않는다 — 왜곡 방지.)

응답 정규화: 여러 기간·우대조건의 금리 행에서 최저~최고를 추출해 상품별 1행으로 요약.
"""
from __future__ import annotations
import logging

import httpx

from app.core.config import get_settings
from app.core.cache import ttl_cached

logger = logging.getLogger(__name__)

# 금리 후보 필드(문서 확인 후 보강). 다양한 표기를 흡수.
RATE_FIELDS = ["lendRate", "loanRate", "rate", "irt", "intRate", "금리", "대출금리"]


def _nums(rows: list[dict]) -> list[float]:
    out = []
    for r in rows:
        for k in RATE_FIELDS:
            v = r.get(k) if isinstance(r, dict) else None
            if v is None:
                continue
            try:
                out.append(float(str(v).replace("%", "").strip()))
            except (TypeError, ValueError):
                pass
    return out


def _rows_from(payload) -> list[dict]:
    # data.go.kr/HF 응답 구조 다양성 흡수: data / items / item / list 등
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
def fetch_policy_products() -> list[dict] | None:
    """디딤돌·보금자리 금리(실연동). 검증된 엔드포인트 미설정/실패 시 None → 예시 폴백."""
    s = get_settings()
    url = s.hf_policy_api_url
    key = s.hf_api_key or s.molit_service_key
    if not url or not key:
        return None
    try:
        r = httpx.get(url, params={"serviceKey": key, "returnType": "JSON",
                                   "page": 1, "perPage": 200}, timeout=12)
        if r.status_code != 200:
            logger.warning("HF 정책금리 %s: %s", r.status_code, r.text[:120])
            return None
        rows = _rows_from(r.json())
        rates = _nums(rows)
        if not rates:
            return None
        lo, hi = round(min(rates), 2), round(max(rates), 2)
        # 단일 엔드포인트가 한 상품을 의미한다고 가정(상품 분리는 문서 확인 후 보강).
        return [{
            "id": "hf_policy", "name": "정책대출(디딤돌·보금자리)", "kind": "정책",
            "rate_min": lo, "rate_max": hi, "method": "원리금균등",
            "limit": None, "req": "무주택·소득/주택가격 요건", "is_sample": False,
            "as_of": None,
        }]
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning("HF 정책금리 호출 실패: %s", e)
        return None
