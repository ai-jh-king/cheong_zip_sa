"""통근권 API.

GET /commute/destinations          선택 가능한 목적지 목록
GET /commute/search                목적지 N분 이내 단지(시세 결합은 프런트/후속)
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.services import commute as commute_svc

router = APIRouter(prefix="/commute", tags=["commute"])

_DISCLAIMER = ("통근시간은 참고용입니다. 'api'는 자동차 길찾기 실측, "
               "'haversine'는 직선거리 기반 추정(우회·평균속도 보정)이며 실제와 다를 수 있습니다.")


@router.get("/destinations")
def destinations(db: Session = Depends(get_db)):
    s = get_settings()
    return {
        "enabled": s.commute_enabled,
        "default_mode": s.commute_default_mode,
        "max_minutes_default": s.commute_max_minutes_default,
        "items": commute_svc.list_destinations(db),
    }


@router.get("/search")
def search(
    dest_id: int = Query(..., description="목적지 id"),
    mode: str = Query("car"),
    max_minutes: int = Query(40, ge=5, le=120),
    property_type: str | None = Query(None),
    limit: int = Query(60, ge=1, le=200),
    db: Session = Depends(get_db),
):
    res = commute_svc.search_by_commute(
        db, dest_id=dest_id, mode=mode, max_minutes=max_minutes,
        property_type=property_type, limit=limit,
    )
    res["disclaimer"] = _DISCLAIMER
    return res
