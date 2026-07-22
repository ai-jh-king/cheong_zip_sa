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
from concurrent.futures import ThreadPoolExecutor

import httpx

from app.core.cache import ttl_cached
from app.core.config import get_settings

logger = logging.getLogger(__name__)
CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"
CATEGORIES = [("SC4", "학교"), ("SW8", "지하철"), ("MT1", "마트"), ("HP8", "병원"), ("AG2", "중개업소")]


@ttl_cached(default_ttl=21600, ttl_attr="cache_ttl_stats_sec")
def nearby(lat: float, lng: float, radius: int = 1500, per: int = 4) -> dict | None:
    """단지 좌표 반경 POI. 좌표를 소수 4자리로 라운딩해 캐시 키 안정화(±11m).
    부하 감사 H1: 캐시 없이 매 상세뷰마다 카카오 5회 순차 호출(최악 40초 스레드 점유,
    쿼터 2만뷰 소진) → ①ttl_cached(단지 좌표는 불변, 6h) ②5개 카테고리 병렬 ③timeout 3초."""
    s = get_settings()
    if not s.kakao_rest_api_key or lat is None or lng is None:
        return None
    lat, lng = round(lat, 4), round(lng, 4)   # 캐시 키 안정화
    headers = {"Authorization": f"KakaoAK {s.kakao_rest_api_key}"}

    def _one(code_label):
        code, label = code_label
        try:
            r = httpx.get(s.kakao_category_url or CATEGORY_URL, headers=headers,
                          params={"category_group_code": code, "x": lng, "y": lat,
                                  "radius": radius, "sort": "distance", "size": per},
                          timeout=3)
            if r.status_code == 200:
                docs = r.json().get("documents", [])
                def _f(v):
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        return None
                return label, [{
                    "name": d.get("place_name"),
                    "distance": int(d.get("distance") or 0),
                    "category": d.get("category_name"),
                    "lat": _f(d.get("y")), "lng": _f(d.get("x")),   # 카카오 x=경도,y=위도 → 지도 마커용
                } for d in docs[:per]], True
        except (httpx.HTTPError, ValueError) as e:
            logger.debug("POI %s 실패: %s", label, e)
        return label, [], False

    with ThreadPoolExecutor(max_workers=len(CATEGORIES)) as ex:
        results = list(ex.map(_one, CATEGORIES))
    out = {label: items for label, items, _ in results}
    any_ok = any(ok for _, _, ok in results)
    return out if any_ok else None
