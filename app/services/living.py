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
NEAR = 150            # 이 거리 이내면 거리점수 만점(변별력 개선: 기존 300m는 대부분 만점→이분법화)
FLOOR_AT_RADIUS = 20  # 반경 끝(1500m)에서의 거리점수
W_DIST, W_DENSITY = 0.6, 0.4   # 카테고리 점수 = 거리 60% + 밀도(반경 내 개수) 40%
DENSITY_CAP = 10               # 반경 내 10개 이상이면 밀도 만점(카카오 meta.total_count 사용)

# (표시 라벨, poi.nearby 의 카테고리 키들, 가중치). 가중치 합 = 1.0
# ⚠️ '교통(지하철)' 항목 제거(2026-07, 실사고): 청주에는 지하철이 없어 전 단지가 교통 0점
#    → 종합점수가 일괄 30% 깎이는 모순(도시에 존재하지 않는 시설로 채점 = 왜곡).
#    0점 처리는 '교통이 나쁘다'는 잘못된 암시라 항목 자체를 제외하고 화면에 사유 고지.
#    (지하철 있는 도시로 확장 시 지역별 카테고리 구성으로 복원 검토)
CATEGORIES = [
    ("편의", ["마트"], 0.35),
    ("학교", ["학교"], 0.35),
    ("의료", ["병원"], 0.30),
]
EXCLUDED_NOTE = "청주에는 지하철이 없어 '교통(지하철)' 항목은 점수에서 제외했습니다(대중교통 접근성은 노선·정류장 기준이 달라 거리 점수로 담지 않음)."


def _sub_score(nearest_m: int | None) -> int:
    if nearest_m is None:
        return 0
    if nearest_m <= NEAR:
        return 100
    if nearest_m >= RADIUS:
        return FLOOR_AT_RADIUS
    span = RADIUS - NEAR
    return round(100 - (nearest_m - NEAR) / span * (100 - FLOOR_AT_RADIUS))


def _density_score(count: int | None) -> int | None:
    """반경 내 개수 → 0~100(10개 이상 만점). None(집계 미제공)이면 None."""
    if count is None:
        return None
    return round(min(count, DENSITY_CAP) / DENSITY_CAP * 100)


def living_score(poi: dict | None) -> dict | None:
    """poi(nearby 결과) → 생활권 점수(거리 60% + 밀도 40%).

    변별력 개선(2026-07, 실사고): 기존 '최단거리 300m=100 / 없음=0' 단독 규칙은 도시 아파트
    대부분이 0 아니면 100으로 몰림 → 만점 문턱 150m 강화 + 반경 내 '개수'(카카오 meta
    total_count, 추가 호출 없음)를 40% 반영. 밀도 미제공(구캐시)이면 거리 100%로 계산(왜곡 없음).
    """
    if poi is None:
        return None
    counts = poi.get("_counts") or {}
    cats = []
    total = 0.0
    for label, keys, weight in CATEGORIES:
        places = []
        cnt_total = None
        for k in keys:
            places += (poi.get(k) or [])
            if counts.get(k) is not None:
                cnt_total = (cnt_total or 0) + counts[k]
        dists = [p.get("distance") for p in places if p.get("distance") is not None]
        nearest = min(dists) if dists else None
        d_sc = _sub_score(nearest)
        c_sc = _density_score(cnt_total)
        sc = round(d_sc * W_DIST + c_sc * W_DENSITY) if c_sc is not None else d_sc
        total += sc * weight
        cats.append({"label": label, "score": sc, "count": cnt_total if cnt_total is not None else len(places),
                     "nearest_m": nearest})
    total = round(total)
    grade = ("최상" if total >= 80 else "좋음" if total >= 60
             else "보통" if total >= 40 else "아쉬움")
    return {"total": total, "grade": grade, "radius": RADIUS, "categories": cats,
            "excluded_note": EXCLUDED_NOTE}
