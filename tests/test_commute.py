"""통근 계산 단위 테스트 — 거리/추정(외부호출 없음).
(실서버에서 pytest 실행. 샌드박스는 httpx 미설치라 import 불가하나 compile은 통과.)
"""
from app.services.commute import haversine_m, estimate_haversine, compute_one


def test_haversine_known_distance():
    # 청주시청 ↔ 충북대: 직선 약 3.2km(±0.5km)
    d = haversine_m(36.6424, 127.4890, 36.6296, 127.4565)
    assert 2700 < d < 3800


def test_haversine_zero():
    assert haversine_m(36.64, 127.49, 36.64, 127.49) == 0


def test_estimate_monotonic_by_distance():
    near = estimate_haversine(36.6424, 127.4890, 36.6296, 127.4565, "car")[0]
    far = estimate_haversine(36.6424, 127.4890, 36.6207, 127.3271, "car")[0]   # 오송역(원거리)
    assert far > near >= 1


def test_estimate_transit_slower_than_car():
    o = (36.6424, 127.4890)
    d = (36.6207, 127.3271)
    car = estimate_haversine(*o, *d, "car")[0]
    transit = estimate_haversine(*o, *d, "transit")[0]
    assert transit > car


def test_compute_one_fallback_method():
    # 키 없는 환경(테스트)에서는 항상 haversine 추정으로 폴백
    r = compute_one(36.6424, 127.4890, 36.6296, 127.4565, "car")
    assert r["method"] == "haversine"
    assert r["minutes"] >= 1 and r["distance_m"] > 0
