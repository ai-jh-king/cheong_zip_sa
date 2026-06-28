"""공동주택관리정보(K-apt) 클라이언트 — 단지 목록 + 기본정보.

흐름: 시군구코드(lawd_cd 5자리) → 단지 목록(kaptCode, kaptName) → kaptCode 로 기본정보.
모두 data.go.kr 공통키(MOLIT_SERVICE_KEY) 사용. 엔드포인트는 설정값(.env)으로 분리해
Swagger 로 확정/조정 가능. URL 미설정·오류 시 빈 결과를 반환(보강은 건너뜀 — 날조하지 않음).

⚠️ 응답은 XML 또는 JSON 일 수 있어 둘 다 관용 처리한다.
"""
from __future__ import annotations
import logging
from urllib.parse import unquote
from xml.etree import ElementTree as ET

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _service_key(s) -> str | None:
    raw = s.molit_service_key
    if not raw:
        return None
    return unquote(raw)  # 인코딩 키여도 디코딩으로 통일


def _get(url: str, params: dict, timeout: int) -> str | None:
    try:
        r = httpx.get(url, params=params, timeout=timeout)
        if r.status_code != 200:
            logger.debug("KAPT %s -> %s: %s", url, r.status_code, r.text[:120])
            return None
        return r.text
    except httpx.HTTPError as e:
        logger.debug("KAPT 요청 실패 %s: %s", url, e)
        return None


def _parse_items(text: str) -> list[dict]:
    """XML 또는 JSON 응답에서 item 리스트 추출(관용)."""
    if not text:
        return []
    t = text.lstrip()
    if t.startswith("{"):
        import json
        try:
            body = json.loads(t)
        except ValueError:
            return []
        items = (((body.get("response") or {}).get("body") or {}).get("items") or {})
        item = items.get("item") if isinstance(items, dict) else items
        if item is None:
            return []
        return item if isinstance(item, list) else [item]
    # XML
    try:
        root = ET.fromstring(t)
    except ET.ParseError:
        return []
    out = []
    for it in root.iter("item"):
        out.append({child.tag: (child.text or "").strip() for child in it})
    return out


def list_complexes(lawd_cd: str) -> list[dict]:
    """시군구(lawd_cd 5자리) 내 단지 목록 [{kaptCode, kaptName}, ...]. 미설정/오류 시 []."""
    s = get_settings()
    url = getattr(s, "kapt_list_url", "")
    key = _service_key(s)
    if not url or not key:
        return []
    text = _get(url, {"serviceKey": key, "sigunguCode": lawd_cd, "numOfRows": 5000, "pageNo": 1},
                getattr(s, "molit_request_timeout", 15))
    items = _parse_items(text)
    out = []
    for it in items:
        code = it.get("kaptCode") or it.get("kapt_code")
        name = it.get("kaptName") or it.get("kapt_name") or it.get("kaptNm")
        if code and name:
            out.append({"kaptCode": code, "kaptName": name})
    return out


def basis_info(kapt_code: str) -> dict | None:
    """kaptCode 의 기본정보 Item dict. 미설정/오류 시 None."""
    s = get_settings()
    url = getattr(s, "kapt_info_url", "")
    key = _service_key(s)
    if not url or not key:
        return None
    text = _get(url, {"serviceKey": key, "kaptCode": kapt_code},
                getattr(s, "molit_request_timeout", 15))
    items = _parse_items(text)
    return items[0] if items else None
