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
        "지하철": [{"distance": 250}],             # 청주엔 지하철이 없어 점수 항목에서 제외됨(아래 검증)
        "마트": [{"distance": 600}],               # 편의
        "학교": [{"distance": 1200}],              # 학교
        "병원": [],                                # 의료 → 0
    }
    res = living_score(poi)
    weights = {label: w for (label, _keys, w) in CATEGORIES}
    expected = round(sum(c["score"] * weights[c["label"]] for c in res["categories"]))
    assert res["total"] == expected
    assert res["grade"] in ("최상", "좋음", "보통", "아쉬움")

    medical = next(c for c in res["categories"] if c["label"] == "의료")
    assert medical["score"] == 0 and medical["count"] == 0


def test_density_mixing_granularity():
    """변별력 회귀: 거리만으로 0/100 이분법이던 것 → 밀도(_counts) 40% 혼합으로 중간 점수 생성."""
    near_but_sparse = living_score({"마트": [{"distance": 100}], "_counts": {"마트": 1},
                                    "학교": [], "병원": []})
    m = next(c for c in near_but_sparse["categories"] if c["label"] == "편의")
    assert m["score"] == 64                      # 거리100(만점)*0.6 + 밀도1개(10)*0.4 = 64 — 더는 무조건 100 아님
    assert m["count"] == 1                       # count 는 반경 내 총 개수(밀도 근거) 노출

    near_and_dense = living_score({"마트": [{"distance": 100}], "_counts": {"마트": 12},
                                   "학교": [], "병원": []})
    m2 = next(c for c in near_and_dense["categories"] if c["label"] == "편의")
    assert m2["score"] == 100                    # 가깝고(150m 이내) 많으면(10개+) 만점

    # 밀도 미제공(구 캐시) → 거리 100%로 폴백(왜곡 없음: 없는 수치를 지어내지 않음)
    legacy = living_score({"마트": [{"distance": 100}], "학교": [], "병원": []})
    m3 = next(c for c in legacy["categories"] if c["label"] == "편의")
    assert m3["score"] == 100


def test_transit_excluded_no_distortion():
    """실사고 회귀: 청주에 없는 지하철로 채점해 전 단지 교통 0점 → 종합 30% 왜곡되던 것.
    교통(지하철) 항목은 점수에서 제외되고, 제외 사유가 응답에 포함되어야 한다."""
    labels = [label for (label, _k, _w) in CATEGORIES]
    assert "교통" not in labels
    assert abs(sum(w for (_l, _k, w) in CATEGORIES) - 1.0) < 1e-9   # 가중치 재분배 합=1

    # 다른 시설이 다 가까우면 지하철이 없어도 만점 가능(왜곡 해소의 핵심)
    res = living_score({"마트": [{"distance": 100}], "학교": [{"distance": 100}],
                        "병원": [{"distance": 100}]})
    assert res["total"] == 100
    assert "지하철" in res["excluded_note"]
