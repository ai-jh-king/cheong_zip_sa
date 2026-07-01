"""생활·교육·운동 시설(Place) API — 단지 주변·지역별 조회.

데이터 없으면 빈 결과(왜곡 방지: 임의 시설 생성 안 함). 좌표 없는 시설은 거리계산 제외.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import places as places_svc

router = APIRouter(prefix="/places", tags=["places"])


@router.get("/near")
def near(lat: float, lng: float,
         radius: int = Query(1200, ge=100, le=5000),
         per: int = Query(6, ge=1, le=20),
         db: Session = Depends(get_db)):
    """좌표 반경 내 시설을 세분류별 거리순."""
    return places_svc.nearby(db, lat, lng, radius, per) or {}


@router.get("/region/{lawd_cd}")
def region(lawd_cd: str, db: Session = Depends(get_db)):
    """구(법정동코드 5자리)별 세분류 개수 요약."""
    return places_svc.by_region(db, lawd_cd)


@router.get("/labels")
def labels():
    """세분류 코드 → 라벨/대분류 매핑(프런트 표시용)."""
    return {k: {"label": v, "group": places_svc.GROUP.get(k, "living")}
            for k, v in places_svc.CATEGORY_LABELS.items()}


@router.get("/fit-categories")
def fit_categories():
    """가족 맞춤 점수 항목 목록(프런트 가중치 입력용)."""
    return {k: places_svc.FIT_LABELS[k] for k in places_svc.FIT_CATEGORIES}


@router.get("/fit-score")
def fit_score(lat: float, lng: float,
              academy: int = 0, sports: int = 0, daycare: int = 0,
              library: int = 0, medical: int = 0, park: int = 0,
              radius: int = Query(1500, ge=300, le=5000),
              db: Session = Depends(get_db)):
    """가족 맞춤 동네 점수. 각 항목 중요도 0~5. 좌표 주변 실제 시설 기반(데이터 없으면 해당 항목 제외)."""
    weights = {"academy": academy, "sports": sports, "daycare": daycare,
               "library": library, "medical": medical, "park": park}
    return places_svc.fit_score(db, lat, lng, weights, radius)
