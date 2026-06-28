"""지도(맵) API — 단지 가격 마커.

주 기능으로서의 지도: 단지별 대표가(중앙값)+좌표를 거래유형/유형 필터로 제공.
좌표 없는 단지는 제외(왜곡 방지). 수치는 실거래 캐시 기반 참고용.
(후속: bbox 뷰포트 로딩·클러스터링 — Phase 2)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import stats

router = APIRouter(prefix="/map", tags=["map"])

DISCLAIMER = ("수치는 신고된 실거래 캐시 기반 참고용이며 신고 지연·정정·해제가 있을 수 있습니다. "
             "좌표가 확인된 단지만 표시되며, 좌표 미확인 단지는 지도에서 제외됩니다(날조 방지).")


@router.get("/markers")
def markers(deal_type: str = Query("trade", description="trade/jeonse/wolse"),
            property_type: str = Query("apartment", description="apartment/officetel/..."),
            db: Session = Depends(get_db)):
    """지도용 단지 마커 목록(거래유형·유형 필터). 대표가는 최근 집계 윈도우 중앙값."""
    return {**stats.map_markers(db, deal_type, property_type), "disclaimer": DISCLAIMER}
