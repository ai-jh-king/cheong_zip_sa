"""단지 상세 API (M3)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import stats
from app.services.poi import nearby
from app.services.living import living_score

router = APIRouter(prefix="/complex", tags=["complex"])

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
    else:
        res["poi"] = None
        res["school_access"] = None
        res["living_score"] = None
    return res
