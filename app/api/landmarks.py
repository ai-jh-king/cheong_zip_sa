"""개발 호재(Landmark) API — 단지 주변·전체(지도). 데이터 없으면 빈 결과."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import landmarks as svc

router = APIRouter(prefix="/landmarks", tags=["landmarks"])


@router.get("")
def list_all(db: Session = Depends(get_db)):
    """활성 호재 전체(지도 핀용)."""
    return svc.all_active(db)


@router.get("/near")
def near(lat: float, lng: float,
         radius: int = Query(4000, ge=500, le=15000),
         db: Session = Depends(get_db)):
    """단지 주변 호재(거리순)."""
    return svc.nearby(db, lat, lng, radius) or []


@router.get("/labels")
def labels():
    return {"category": svc.CATEGORY_LABELS, "status": svc.STATUS_LABELS}
