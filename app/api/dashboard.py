"""대시보드 집계 API (M2). 웹/앱 공유."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import stats
from app.services.geocode import coords_map


def _attach_coords(cmap: dict, items: list[dict]) -> list[dict]:
    """좌표 있는 단지만 lat/lng 부여(없으면 None — 지도에 안 찍힘)."""
    for it in items:
        c = cmap.get((it.get("complex_name"), it.get("lawd_cd")))
        it["lat"], it["lng"] = (c if c else (None, None))
    return items

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DISCLAIMER = ("수치는 신고된 실거래 캐시 기반 참고용이며 신고 지연·정정·해제가 있을 수 있습니다. "
              "자료: 국토교통부 실거래가. 표본이 적으면 평균·등락폭의 변동성이 큽니다.")


def _has_sample(db: Session, ptype: str) -> bool:
    from sqlalchemy import select, exists
    from app.models import Transaction
    return bool(db.scalar(select(exists().where(
        Transaction.property_type == ptype, Transaction.is_sample.is_(True)))))


@router.get("/summary")
def summary(db: Session = Depends(get_db),
            property_type: str = Query("apartment")):
    city = stats.city_summary(db, property_type)
    regions = stats.by_region(db, property_type)
    return {
        "disclaimer": DISCLAIMER,
        "property_type": property_type,
        "contains_sample_data": _has_sample(db, property_type),
        "city": city,
        "by_region": regions,
    }


@router.get("/trend")
def trend(db: Session = Depends(get_db),
          property_type: str = Query("apartment"),
          months: int = Query(6, ge=1, le=24)):
    res = stats.trend(db, property_type, months)
    res["disclaimer"] = DISCLAIMER
    res["property_type"] = property_type
    return res


@router.get("/ranking")
def ranking(db: Session = Depends(get_db),
            property_type: str = Query("apartment", description="apartment/officetel/rowhouse/detached/all"),
            limit: int = Query(15, ge=1, le=500),
            area_band: str = Query("all", description="all/small/medium/large")):
    """랭킹 화면: 매매가순·평단가순·등락·거래활발구·신고가."""
    pt = property_type
    pt_for_complex = pt if pt != "all" else "apartment"
    cmap = coords_map(db)
    return {
        "disclaimer": DISCLAIMER,
        "property_type": pt, "area_band": area_band,
        "contains_sample_data": _has_sample(db, pt_for_complex),
        "top_trades": _attach_coords(cmap, stats.top_trades(db, pt, limit, area_band)),
        "top_by_ppm": _attach_coords(cmap, stats.top_trades_by_ppm(db, pt, limit, area_band)),
        "active_regions": stats.active_regions(db, "all"),
        "top_movers": stats.complex_movers(db, pt_for_complex, 10),
        "newly_high": stats.newly_high(db, pt_for_complex, 10),
        "newly_low": stats.newly_low(db, pt_for_complex, 10),
    }


@router.get("/overview")
def overview(db: Session = Depends(get_db),
             property_type: str = Query("apartment")):
    """홈 화면: 평형대별 평단가(중앙값)·거래량·오늘의 하이라이트."""
    movers = stats.complex_movers(db, property_type, 1)
    actives = stats.active_regions(db, "all")
    highs = stats.newly_high(db, property_type, 5)
    return {
        "disclaimer": DISCLAIMER,
        "property_type": property_type,
        "contains_sample_data": _has_sample(db, property_type),
        "area_ppm": stats.ppm_by_area(db, property_type),
        "volume": stats.volume(db, property_type),
        "active_top": actives[0] if actives else None,
        "mover_top": movers[0] if movers else None,
        "newly_high": highs,
    }


@router.get("/heatmap")
def heatmap(db: Session = Depends(get_db),
            property_type: str = Query("apartment")):
    """평단가(만원/평) 히트맵: 좌표 있는 단지별 중앙값. 지오코딩 필요."""
    return {**stats.heatmap(db, property_type), "disclaimer": DISCLAIMER,
            "property_type": property_type}


@router.get("/distribution")
def distribution(db: Session = Depends(get_db),
                 property_type: str = Query("apartment"),
                 deal_type: str = Query("trade"),
                 gu: str = Query(""),
                 area_band: str = Query("all")):
    """가격 분포 히스토그램: 매매가/전세보증금/월세의 가격대별 거래건수 + 중앙값·사분위.
    표본 8건 미만이면 buckets=None(표본 부족·왜곡 방지)."""
    return {**stats.price_distribution(db, property_type, deal_type,
                                       gu or None, area_band),
            "disclaimer": DISCLAIMER}


@router.get("/board")
def board(db: Session = Depends(get_db),
          property_type: str = Query("apartment")):
    """홈 대시보드: 전체 매매 추이 · 구별 매매/평단가 랭킹 · 구별 최신 실거래.
    구 정렬은 '평단가 랭킹 순서'로 전 섹션 통일(추후 확장 시에도 동일 기준)."""
    gu_ranking = stats.gu_price_ranking(db, property_type)
    order = {g["code"]: i for i, g in enumerate(gu_ranking)}          # 통일 기준
    recent = stats.recent_trades(db, property_type, 4)
    recent.sort(key=lambda r: order.get(r["code"], 999))
    gu_trend = stats.trend(db, property_type, 12)
    gu_trend["series"].sort(key=lambda s: order.get(s["code"], 999))  # 추이 범례도 동일 순서
    return {
        "disclaimer": DISCLAIMER, "property_type": property_type,
        "contains_sample_data": _has_sample(db, property_type),
        "city": stats.city_summary(db, property_type),   # 홈 히어로(청주 전체 요약)
        "city_trend": stats.city_trend(db, property_type, 12),
        "landmark": stats.landmark_apts(db, property_type, 5),
        "trending": stats.trending_complexes(db, property_type, 8),
        "top_movers": stats.top_movers(db, property_type, 10),
        "landmark_by_band": stats.landmark_by_band(db, property_type, 5),
        "recent_by_band": stats.recent_by_band(db, property_type, 5),
        "gu_trend": gu_trend,
        "gu_ranking": gu_ranking,
        "recent_by_gu": recent,
        "gu_order": [g["code"] for g in gu_ranking],
        "volume": stats.volume(db, property_type),
    }
