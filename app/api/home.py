"""홈 피드 API (M2 UI / 청약·뉴스 실연동 M4)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import stats
from app.sources.applyhome import fetch_subscriptions, fetch_competition, attach_competition
from app.sources.news import fetch_news
from app.data.sample_feed import SUBSCRIPTIONS, NEWS, POLICIES

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/feed")
def feed(db: Session = Depends(get_db), property_type: str = Query("apartment")):
    ap = stats.ppm_by_area(db, property_type)
    vol = stats.volume(db, property_type)
    actives = stats.active_regions(db, "all")
    medium = next((b for b in ap["buckets"] if b["bucket"] == "medium"), None)

    # 키 있으면 실데이터, 없거나 실패하면 예시로 폴백
    subs_live = fetch_subscriptions(limit=10)
    if subs_live is not None:
        subs_live = attach_competition(subs_live, fetch_competition())
    news_live = fetch_news(limit=6)
    subscriptions = subs_live if subs_live is not None else SUBSCRIPTIONS
    news = news_live if news_live is not None else NEWS
    policies = POLICIES  # 정책은 큐레이션(예시) 유지

    return {
        "pulse": {
            "property_type": property_type,
            "median_pyeong": ap["total_median_pyeong"],
            "median_pyeong_medium": medium["median_pyeong"] if medium else None,
            "count": ap["total_count"],
            "volume": vol,
            "active_top": actives[0] if actives else None,
        },
        "subscriptions": subscriptions,
        "news": news,
        "policies": policies,
        "subs_live": subs_live is not None,
        "news_live": news_live is not None,
        "data_pending": (subs_live is None) or (news_live is None),
        "notice": ("청약·뉴스 일부는 준비중입니다. ‘예시’ 배지가 붙은 항목은 실제 정보가 아닙니다. "
                   "실연동: 청약홈 API(data.go.kr) · 네이버 뉴스 API."),
    }

