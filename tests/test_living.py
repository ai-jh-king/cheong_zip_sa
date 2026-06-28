"""생활권 점수(거리 기반) 단위 테스트 — DB 불필요."""
from app.services.living import (
    living_score, _sub_score, CATEGORIES, RADIUS, NEAR, FLOOR_AT_RADIUS,
)


def test_sub_score_bounds():
    assert _sub_score(None) == 0
    assert _sub_score(NEAR) == 100
    assert _sub_score(NEAR - 50) == 100          # 가까우면 만점
    assert _sub_score(RADIUS) == FLOOR_AT_RADIUS
    mid = _sub_score(900)
    assert FLOOR_AT_RADIUS < mid < 100           # 중간 거리는 중간 점수


def test_living_score_none_and_empty():
    assert living_score(None) is None
    empty = living_score({})
    assert empty is not None and empty["total"] == 0   # 시설 없음 → 0점


def test_living_score_weighted_total():
    poi = {
        "지하철": [{"distance": 250}],             # 교통 → 100
        "마트": [{"distance": 600}],               # 편의
        "학교": [{"distance": 1200}],              # 학교
        "병원": [],                                # 의료 → 0
    }
    res = living_score(poi)
    weights = {label: w for (label, _keys, w) in CATEGORIES}
    expected = round(sum(c["score"] * weights[c["label"]] for c in res["categories"]))
    assert res["total"] == expected
    assert res["grade"] in ("최상", "좋음", "보통", "아쉬움")

    transit = next(c for c in res["categories"] if c["label"] == "교통")
    assert transit["score"] == 100 and transit["nearest_m"] == 250
    medical = next(c for c in res["categories"] if c["label"] == "의료")
    assert medical["score"] == 0 and medical["count"] == 0
