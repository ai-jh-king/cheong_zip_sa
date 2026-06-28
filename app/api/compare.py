"""단지 비교 API — 여러 단지를 나란히 비교(경량 요약)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import stats

router = APIRouter(prefix="/compare", tags=["compare"])

MAX_ITEMS = 4


class CompareItem(BaseModel):
    name: str
    lawd_cd: str
    property_type: str = "apartment"


class CompareRequest(BaseModel):
    items: list[CompareItem] = Field(default_factory=list)


@router.post("")
def compare(req: CompareRequest, db: Session = Depends(get_db)):
    """최대 4개 단지의 핵심 지표를 반환. 거래 없는 단지는 found=False."""
    items = req.items[:MAX_ITEMS]
    out = [stats.compare_one(db, it.name, it.lawd_cd, it.property_type) for it in items]
    return {
        "items": out,
        "disclaimer": "신고된 실거래 캐시 기반 참고용입니다(신고 지연·정정·해제 가능). 자료: 국토교통부 실거래가.",
    }
