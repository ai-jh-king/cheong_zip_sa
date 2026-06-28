"""생활권 점수 — 단지 주변 인프라(POI) 접근성을 투명하게 점수화.

설계(왜곡 없음):
  - 입력은 poi.nearby() 결과(반경 1.5km 내 카테고리별 장소+거리). 임의 장소를 만들지 않음.
  - 점수는 '가장 가까운 시설까지의 거리' 기반의 단순·공개 규칙. 블랙박스 아님.
      300m 이내 = 100점, 1500m = 40점(선형), 반경 내 시설 없음 = 0점.
  - 카테고리: 교통(지하철)·편의(마트)·의료(병원)·학교. 가중 평균으로 종합.
  - 결과에 카테고리별 점수·최단거리·개수를 함께 반환해 '왜 이 점수인지' 보이게 함.
  - 실거주 만족도(소음·평판 등)와 다를 수 있는 '거리 기준 참고치'임을 화면에서 고지.

주의: poi.nearby 는 카테고리당 상위 N개(기본 4)만 주므로 개수는 밀도가 아니라 참고용.
"""
from __future__ import annotations

RADIUS = 1500
NEAR = 300            # 이 거리 이내면 만점
FLOOR_AT_RADIUS = 40  # 반경 끝(1500m)에서의 점수

# (표시 라벨, poi.nearby 의 카테고리 키들, 가중치). 가중치 합 = 1.0
CATEGORIES = [
    ("교통", ["지하철"], 0.30),
    ("편의", ["마트"], 0.25),
    ("학교", ["학교"], 0.25),
    ("의료", ["병원"], 0.20),
]


def _sub_score(nearest_m: int | None) -> int:
    if nearest_m is None:
        return 0
    if nearest_m <= NEAR:
        return 100
    if nearest_m >= RADIUS:
        return FLOOR_AT_RADIUS
    span = RADIUS - NEAR
    return round(100 - (nearest_m - NEAR) / span * (100 - FLOOR_AT_RADIUS))


def living_score(poi: dict | None) -> dict | None:
    """poi(nearby 결과) → 생활권 점수. poi 없으면 None(화면에서 '정보 필요' 안내)."""
    if poi is None:
        return None
    cats = []
    total = 0.0
    for label, keys, weight in CATEGORIES:
        places = []
        for k in keys:
            places += (poi.get(k) or [])
        dists = [p.get("distance") for p in places if p.get("distance") is not None]
        nearest = min(dists) if dists else None
        sc = _sub_score(nearest)
        total += sc * weight
        cats.append({"label": label, "score": sc, "count": len(places), "nearest_m": nearest})
    total = round(total)
    grade = ("최상" if total >= 80 else "좋음" if total >= 60
             else "보통" if total >= 40 else "아쉬움")
    return {"total": total, "grade": grade, "radius": RADIUS, "categories": cats}
