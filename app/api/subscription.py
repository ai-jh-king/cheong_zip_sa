"""청약·분양 정식 탭 API — 청주 지역 청약 공고 목록.

소스: 한국부동산원 청약홈(applyhome). 키 없거나 실패 시 예시 데이터(is_sample=True) 폴백.
경쟁률·당첨가점은 별도 API 연동 시 attach_competition 으로 채워진다(미연동이면 None).
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.sources.applyhome import (fetch_subscriptions, fetch_competition,
                                   attach_competition)
from app.data.sample_feed import SUBSCRIPTIONS

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("")
def list_subscriptions(limit: int = Query(50, ge=1, le=100)):
    subs = fetch_subscriptions(limit=limit)
    live = subs is not None
    if live:
        subs = attach_competition(subs, fetch_competition())
    items = subs if live else SUBSCRIPTIONS  # 미연동 시 예시(배지 표기)
    return {
        "items": items or [],
        "live": live,
        "notice": None if live else "청약홈 API 미연동 — 아래는 예시입니다(키 설정 시 실데이터).",
        "disclaimer": ("자료: 한국부동산원 청약홈. 일정·경쟁률·가점은 갱신 지연이 있을 수 있어 "
                       "최종은 청약홈에서 확인하세요."),
    }
