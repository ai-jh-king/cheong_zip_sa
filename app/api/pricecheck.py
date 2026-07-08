"""가격 검증 API — 호가 검증·구 시세 맥락·급매 레이더(판정 없음·사실+면책)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import pricecheck as svc

router = APIRouter(prefix="/pricecheck", tags=["pricecheck"])


@router.get("/quote")
def quote(name: str, lawd_cd: str, asking: int = Query(..., ge=1000, description="호가(만원)"),
          property_type: str = "apartment", db: Session = Depends(get_db)):
    return svc.quote_check(db, name, lawd_cd, asking, property_type)


@router.get("/gu-context")
def gu_ctx(db: Session = Depends(get_db)):
    return svc.gu_context(db)


@router.get("/bargains")
def bargains(months: int = Query(3, ge=1, le=12), limit: int = Query(12, ge=1, le=30),
             db: Session = Depends(get_db)):
    return svc.bargain_radar(db, months=months, limit=limit)
