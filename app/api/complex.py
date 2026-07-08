"""단지 상세 API (M3)."""
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import stats
from app.services.poi import nearby
from app.services import places as places_svc
from app.services import landmarks as landmarks_svc
from app.services import commute as commute_svc
from app.services.living import living_score

router = APIRouter(prefix="/complex", tags=["complex"])


@router.post("/quotes")
def quotes(payload: dict = Body(...), db: Session = Depends(get_db)):
    """여러 단지의 최근 매매가·전월대비를 한 번에(관심단지 목록 등).
    body: {"items":[{"name":..,"lawd_cd":..,"property_type":..}, ...]}"""
    items = (payload or {}).get("items") or []
    return stats.complex_quotes(db, items)

DISCLAIMER = ("단지 상세는 신고된 실거래 캐시 기반 참고용입니다(신고 지연·정정·해제 가능). "
              "자료: 국토교통부 실거래가.")


def _school_summary(schools: list[dict]) -> dict | None:
    """인근 학교(카카오 장소) → 통학 접근성 요약. 거리 기준일 뿐 학업성취 아님(왜곡 방지)."""
    if not schools:
        return None
    def _nearest(keyword):
        cand = [s for s in schools if keyword in (s.get("name") or "")]
        return ({"name": cand[0]["name"], "distance": cand[0]["distance"]} if cand else None)
    nearest = min(schools, key=lambda s: s.get("distance") or 10**9)
    return {
        "count": len(schools),
        "nearest": {"name": nearest.get("name"), "distance": nearest.get("distance")},
        "elementary": _nearest("초등"),
        "middle": _nearest("중학"),
        "high": _nearest("고등"),
        "note": "통학 접근성(거리 기준) · 자료: 카카오 장소",
    }


@router.get("/detail")
def detail(db: Session = Depends(get_db),
           name: str = Query(...),
           lawd_cd: str = Query(...),
           property_type: str | None = Query(None)):
    res = stats.complex_detail(db, name, lawd_cd, property_type)
    res["disclaimer"] = DISCLAIMER
    # 좌표가 있으면 주변 인프라(카카오) 부가 — 키 없으면 None
    if res.get("found") and res.get("lat") and res.get("lng"):
        res["poi"] = nearby(res["lat"], res["lng"])
        res["school_access"] = _school_summary((res["poi"] or {}).get("학교") or [])
        res["living_score"] = living_score(res["poi"])
        res["places"] = places_svc.nearby(db, res["lat"], res["lng"])  # 공공데이터 학원·체육·생활
        res["landmarks"] = landmarks_svc.nearby(db, res["lat"], res["lng"])  # 주변 개발 호재
        res["work_access"] = commute_svc.hub_access(db, res["lat"], res["lng"])  # 청주 직장·거점 거리(직선)
    else:
        res["poi"] = None
        res["school_access"] = None
        res["places"] = None
        res["landmarks"] = None
        res["living_score"] = None
        res["work_access"] = None
    return res
