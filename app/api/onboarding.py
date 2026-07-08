"""청주 전입자 온보딩 API — '청주가 처음이세요?'

GET  /onboarding/options              직장·산단 선택지(1단계)
GET  /onboarding/recommend            직장 근처 + 시세 + 예산 차액 큐레이션(결과)

왜곡 없음: 새 데이터 생성 없이 기존 통근검색·시세 조립. 판정 대신 참고 정보 + 고지.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import onboarding as svc

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/options")
def options(db: Session = Depends(get_db)):
    return svc.options(db)


@router.get("/recommend")
def recommend(dest_key: str = Query(..., description="직장·산단 key(/onboarding/options)"),
              budget: int | None = Query(None, ge=0, description="보유현금(만원, 선택)"),
              has_kids: bool = Query(False),
              mode: str = Query("driving", description="driving/transit"),
              max_minutes: int = Query(30, ge=5, le=90),
              limit: int = Query(8, ge=1, le=20),
              db: Session = Depends(get_db)):
    return svc.recommend(db, dest_key, budget=budget, has_kids=has_kids,
                         mode=mode, max_minutes=max_minutes, limit=limit)
