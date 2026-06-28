"""
네이버 뉴스 검색 커넥터 (홈 피드용).

원칙
  - 저작권: 제목 + 짧은 요약 + 출처 링크만 저장(원문 전재 금지 — 지침서 8장).
  - 키(NAVER_SEARCH_CLIENT_ID/SECRET) 없거나 호출 실패 시 None 반환 → 피드는 예시로 폴백.
"""
from __future__ import annotations
import html
import logging
import re
from datetime import datetime
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.cache import ttl_cached

logger = logging.getLogger(__name__)
NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
_TAG = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return html.unescape(_TAG.sub("", s or "")).strip()


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.replace("www.", "")
        return host or "뉴스"
    except Exception:
        return "뉴스"


def _date(pub: str) -> str:
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(pub, fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return (pub or "")[:16]


@ttl_cached("cache_ttl_news_sec", 600)
def fetch_news(query: str = "청주 부동산", limit: int = 6) -> list[dict] | None:
    s = get_settings()
    if not (s.naver_search_client_id and s.naver_search_client_secret):
        return None
    try:
        r = httpx.get(s.news_url or NEWS_URL, params={"query": query, "display": limit, "sort": "date"},
                      headers={"X-Naver-Client-Id": s.naver_search_client_id,
                               "X-Naver-Client-Secret": s.naver_search_client_secret},
                      timeout=10)
        if r.status_code != 200:
            logger.warning("네이버 뉴스 %s: %s", r.status_code, r.text[:120])
            return None
        items = r.json().get("items", [])
        out = []
        for it in items:
            link = it.get("originallink") or it.get("link") or ""
            out.append({
                "title": _clean(it.get("title", "")),
                "summary": _clean(it.get("description", ""))[:120],  # 짧은 요약만
                "source": _domain(link), "url": link,
                "date": _date(it.get("pubDate", "")), "category": "뉴스",
                "is_sample": False,
            })
        return out or None
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("네이버 뉴스 호출 실패: %s", e)
        return None
