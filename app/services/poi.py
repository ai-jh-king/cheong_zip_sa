"""
단지 주변 인프라(POI) — 카카오 로컬 '카테고리로 장소 검색'.
좌표(위도/경도) 기준 반경 내 학교·지하철·마트·병원을 거리순으로.

키: KAKAO_REST_API_KEY. (지오코딩은 네이버 우선이지만, '반경+카테고리' POI 검색은
      네이버 클라우드에 동등 API가 없어 인근 인프라/중개업소는 카카오를 사용한다.)
실패/키없음 시 None → 화면에서 '인프라 정보 없음/키 필요'로 안내(왜곡 방지: 임의 장소 안 만듦).
주의: 카카오는 x=경도(lng), y=위도(lat).
"""
from __future__ import annotations
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"
CATEGORIES = [("SC4", "학교"), ("SW8", "지하철"), ("MT1", "마트"), ("HP8", "병원"), ("AG2", "중개업소")]


def nearby(lat: float, lng: float, radius: int = 1500, per: int = 4) -> dict | None:
    s = get_settings()
    if not s.kakao_rest_api_key or lat is None or lng is None:
        return None
    headers = {"Authorization": f"KakaoAK {s.kakao_rest_api_key}"}
    out: dict[str, list] = {}
    any_ok = False
    for code, label in CATEGORIES:
        try:
            r = httpx.get(s.kakao_category_url or CATEGORY_URL, headers=headers,
                          params={"category_group_code": code, "x": lng, "y": lat,
                                  "radius": radius, "sort": "distance", "size": per},
                          timeout=8)
            if r.status_code == 200:
                any_ok = True
                docs = r.json().get("documents", [])
                out[label] = [{
                    "name": d.get("place_name"),
                    "distance": int(d.get("distance") or 0),
                    "category": d.get("category_name"),
                } for d in docs[:per]]
            else:
                out[label] = []
        except (httpx.HTTPError, ValueError) as e:
            logger.debug("POI %s 실패: %s", label, e)
            out[label] = []
    return out if any_ok else None
