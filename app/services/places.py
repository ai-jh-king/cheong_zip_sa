"""생활·교육·운동 시설(Place) 조회 — 단지 주변·지역별 요약.

좌표 기준 반경 내 시설을 세분류별 거리순으로. 좌표 없는 시설은 제외(왜곡 방지).
공개 데이터 + 향후 등록(source) 통합. 분류는 공공데이터 분야/과정 텍스트의 키워드 매핑.
"""
from __future__ import annotations
from math import radians, sin, cos, asin, sqrt

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import Place

# 세분류 → 한글 라벨
CATEGORY_LABELS = {
    "academy_exam": "입시·보습", "academy_lang": "외국어", "academy_art": "예체능",
    "academy_pe": "체육·운동", "academy_it": "컴퓨터", "academy_etc": "기타학원",
    "sports": "체육시설", "library": "도서관", "hospital": "병원·의원",
    "pharmacy": "약국", "daycare": "어린이집·유치원", "culture": "문화·복지",
}
# 세분류 → 대분류
GROUP = {
    "academy_exam": "education", "academy_lang": "education", "academy_art": "education",
    "academy_pe": "education", "academy_it": "education", "academy_etc": "education",
    "sports": "sports", "library": "living", "hospital": "living",
    "pharmacy": "living", "daycare": "living", "culture": "living",
}


def classify_academy(field: str | None, course: str | None) -> str:
    """학원 분야/과정 텍스트 → 세분류(키워드 매핑, 실패 시 기타학원).
    공공데이터 분야/계열/과정 필드명이 데이터셋마다 달라도 텍스트 키워드로 견고하게 분류."""
    t = f"{field or ''} {course or ''}"

    def has(*ks):
        return any(k in t for k in ks)

    if has("외국어", "영어", "중국어", "일본어", "국제"):
        return "academy_lang"
    if has("태권도", "검도", "합기도", "유도", "수영", "축구", "농구", "체육", "요가",
           "필라테스", "줄넘기", "골프", "무도", "복싱", "헬스"):
        return "academy_pe"
    if has("음악", "미술", "피아노", "바이올린", "성악", "서예", "사진", "예능",
           "공예", "무용", "발레", "디자인", "방송"):
        return "academy_art"
    if has("컴퓨터", "코딩", "정보", "프로그래밍", "IT"):
        return "academy_it"
    if has("입시", "보습", "검정", "종합", "논술", "수학", "과학", "국어",
           "교과", "학습", "독서", "한자"):
        return "academy_exam"
    return "academy_etc"


def _haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    a = (sin(radians(lat2 - lat1) / 2) ** 2
         + cos(p1) * cos(p2) * sin(radians(lng2 - lng1) / 2) ** 2)
    return 2 * r * asin(sqrt(a))


def nearby(db: Session, lat: float, lng: float, radius: int = 1200, per: int = 6) -> dict | None:
    """좌표 반경(m) 내 시설을 세분류별 거리순. 좌표 없으면 None, 데이터 없으면 {}."""
    if lat is None or lng is None:
        return None
    # bbox 선필터(인덱스 활용) 후 정확 거리(haversine). 청주 위도 대략 보정.
    dlat = radius / 111_000.0
    dlng = radius / 88_000.0
    rows = db.execute(
        select(Place.subcategory, Place.name, Place.lat, Place.lng,
               Place.course, Place.tuition, Place.source).where(
            Place.lat.isnot(None), Place.lng.isnot(None),
            Place.lat.between(lat - dlat, lat + dlat),
            Place.lng.between(lng - dlng, lng + dlng),
        )
    ).all()
    buckets: dict[str, list] = {}
    for p in rows:
        d = _haversine_m(lat, lng, p.lat, p.lng)
        if d > radius:
            continue
        buckets.setdefault(p.subcategory, []).append({
            "name": p.name, "distance": int(d), "course": p.course,
            "tuition": p.tuition, "source": p.source,
        })
    out: dict[str, dict] = {}
    for sub, items in buckets.items():
        items.sort(key=lambda x: x["distance"])
        out[sub] = {"label": CATEGORY_LABELS.get(sub, sub), "group": GROUP.get(sub, "living"),
                    "count": len(items), "items": items[:per]}
    return out


def by_region(db: Session, lawd_cd: str) -> dict:
    """구(lawd_cd)별 세분류 개수 요약(동네 밀집도)."""
    rows = db.execute(
        select(Place.subcategory, func.count())
        .where(Place.lawd_cd == lawd_cd)
        .group_by(Place.subcategory)
    ).all()
    return {sub: {"label": CATEGORY_LABELS.get(sub, sub), "group": GROUP.get(sub, "living"),
                  "count": n} for sub, n in rows}


# ── 가족 맞춤 동네 점수 ──────────────────────────────────────────────
# 사용자가 중요시하는 생활 항목에 가중치를 주면, 단지 주변 '실제' 시설로 투명하게 점수화한다.
# 왜곡 없음: 실제 개수·거리 기반. 데이터 없는 항목은 점수를 지어내지 않고 '데이터 없음'으로 제외.
FIT_CATEGORIES = {                       # 노출 항목 → 포함 subcategory
    "academy": ["academy_exam", "academy_lang", "academy_art", "academy_it", "academy_etc"],
    "sports":  ["sports", "academy_pe"],
    "daycare": ["daycare"],
    "library": ["library"],
    "medical": ["hospital", "pharmacy"],
    "park":    ["park"],
}
FIT_LABELS = {"academy": "학원·교육", "sports": "운동", "daycare": "어린이집·유치원",
              "library": "도서관", "medical": "병원·약국", "park": "공원·놀이터"}


def fit_score(db: Session, lat: float, lng: float, weights: dict, radius: int = 1500) -> dict:
    """가족 맞춤 동네 점수. weights: {항목: 중요도 0~5}. 좌표 없으면 None.
    각 항목 subscore(0~100) = 근접도 60% + 밀집도 40%. 데이터 없는 항목은 제외(왜곡 방지).
    overall = 가중평균(데이터 있는 항목만)."""
    if lat is None or lng is None:
        return {"overall": None, "categories": {}, "note": "좌표 없음"}
    near = nearby(db, lat, lng, radius, per=50) or {}
    cats: dict[str, dict] = {}
    total_w = 0.0
    total_s = 0.0
    for cat, subs in FIT_CATEGORIES.items():
        w = float(weights.get(cat, 0) or 0)
        if w <= 0:
            continue
        items: list = []
        for sub in subs:
            if sub in near:
                items += near[sub]["items"]
        if not items:                    # 데이터 없음 → 점수 산정 제외
            cats[cat] = {"label": FIT_LABELS[cat], "weight": w, "count": 0,
                         "nearest": None, "score": None, "note": "데이터 없음"}
            continue
        items.sort(key=lambda x: x["distance"])
        cnt = len(items)
        nearest = items[0]["distance"]
        prox = max(0.0, 100.0 - nearest / (radius / 100.0))   # 0m→100, radius→0
        dens = min(100.0, cnt * 20.0)                          # 5개↑ 만점
        sub_s = round(0.6 * prox + 0.4 * dens)
        cats[cat] = {"label": FIT_LABELS[cat], "weight": w, "count": cnt,
                     "nearest": nearest, "score": sub_s}
        total_w += w
        total_s += w * sub_s
    overall = round(total_s / total_w) if total_w > 0 else None
    return {"overall": overall, "radius": radius, "categories": cats}


def in_bounds(db: Session, min_lat: float, max_lat: float,
              min_lng: float, max_lng: float,
              groups: list[str] | None = None, limit: int = 500) -> dict:
    """지도 영역(bounding box) 안의 시설 마커 목록. groups로 대분류(education/sports/living) 필터.
    데이터가 없으면 places=[] (구조만 존재 → 데이터 적재 시 자동 표출)."""
    if None in (min_lat, max_lat, min_lng, max_lng):
        return {"places": []}
    q = select(Place.name, Place.category, Place.subcategory,
               Place.lat, Place.lng, Place.source).where(
        Place.lat.isnot(None), Place.lng.isnot(None),
        Place.lat.between(min_lat, max_lat),
        Place.lng.between(min_lng, max_lng))
    if groups:
        q = q.where(Place.category.in_(groups))
    rows = db.execute(q.limit(limit)).all()
    return {"places": [
        {"name": r.name, "category": r.category, "subcategory": r.subcategory,
         "label": CATEGORY_LABELS.get(r.subcategory, r.subcategory),
         "lat": r.lat, "lng": r.lng, "source": r.source}
        for r in rows]}
