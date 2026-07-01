"""개발 호재(Landmark) 조회 — 단지 주변·전체(지도용).

왜곡 없음: status(확정/추진/계획)·출처를 그대로 노출. 점수화·집값 단정 없음(사실 표시만).
좌표 없으면 거리 계산 제외. 데이터 없으면 빈 결과(임의 생성 안 함).
"""
from __future__ import annotations
from math import radians, sin, cos, asin, sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Landmark

CATEGORY_LABELS = {"industry": "산업", "transport": "교통", "commercial": "상업",
                   "residential": "주거", "public": "공공"}
STATUS_LABELS = {"confirmed": "확정", "ongoing": "추진", "planned": "계획"}


def _haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    a = (sin(radians(lat2 - lat1) / 2) ** 2
         + cos(p1) * cos(p2) * sin(radians(lng2 - lng1) / 2) ** 2)
    return 2 * r * asin(sqrt(a))


def _dump(l: Landmark, distance: int | None = None) -> dict:
    return {
        "id": l.id, "name": l.name,
        "category": l.category, "category_label": CATEGORY_LABELS.get(l.category, l.category),
        "status": l.status, "status_label": STATUS_LABELS.get(l.status, l.status),
        "summary": l.summary, "expected_year": l.expected_year,
        "source_name": l.source_name, "source_url": l.source_url,
        "lat": l.lat, "lng": l.lng, "distance": distance,
    }


def all_active(db: Session) -> list[dict]:
    """활성 호재 전체(지도 핀용). 정렬: sort_order → 연도."""
    rows = db.execute(
        select(Landmark).where(Landmark.is_active.is_(True))
        .order_by(Landmark.sort_order, Landmark.expected_year)
    ).scalars().all()
    return [_dump(l) for l in rows]


def nearby(db: Session, lat: float, lng: float, radius: int = 4000, limit: int = 8) -> list[dict] | None:
    """단지 주변 호재(거리순). 청주는 호재가 광역 영향이라 반경 기본 4km. 좌표 없으면 None."""
    if lat is None or lng is None:
        return None
    rows = db.execute(
        select(Landmark).where(Landmark.is_active.is_(True),
                               Landmark.lat.isnot(None), Landmark.lng.isnot(None))
    ).scalars().all()
    out = []
    for l in rows:
        d = _haversine_m(lat, lng, l.lat, l.lng)
        if d <= radius:
            out.append(_dump(l, int(d)))
    out.sort(key=lambda x: x["distance"])
    return out[:limit]
