"""시세 탭(지역→단지 드릴다운) 서버 집계 API.

클라이언트가 거래 전량을 받아 집계하던 구조를 대체(확장성):
구/유형/평형대만 넘기면 서버가 윈도우 내 실거래로 요약+단지 리스트를 집계해 반환.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import stats

router = APIRouter(prefix="/price", tags=["price"])

_VALID_BANDS = {"all", "small", "medium", "large"}


@router.get("/overview")
def price_overview(
    db: Session = Depends(get_db),
    lawd_cd: str | None = Query(None, description="법정동 앞 5자리(구). 미지정=청주 전체"),
    property_type: str = Query("apartment"),
    band: str = Query("all"),
):
    band = band if band in _VALID_BANDS else "all"
    pt = "all" if property_type in ("전체", "all", "", None) else property_type
    return stats.price_overview(db, lawd_cd=lawd_cd, property_type=pt, band=band)
