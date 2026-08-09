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


def test_gu_label_is_string():
    """_gu 는 District 객체가 아니라 이름 문자열 — 객체 반환 시 프런트에 '[object Object]' 표출(실사고)."""
    from app.services.commute import _gu
    assert _gu("43113") == "흥덕구"
    assert isinstance(_gu("43113"), str)
    assert _gu("99999") == ""


def test_search_attaches_price_by_name_not_fk(db):
    """시세 조인은 (단지명, lawd_cd) — Transaction.complex_id 는 수집이 채우지 않아
    FK 로 묶으면 가격이 전부 None('—')이 되는 실사고(v1.254) 회귀 방지."""
    from datetime import date
    from app.models import Complex, CommuteDestination, Transaction
    db.add(CommuteDestination(id=901, key="t_job", name="테스트직장", category="job",
                              lat=36.64, lng=127.43, is_active=True, sort_order=1))
    db.add(Complex(name="통근테스트단지", lawd_cd="43113", property_type="apartment",
                   dong="가경동", lat=36.641, lng=127.431))
    for i, amt in enumerate([30000, 32000, 34000]):
        db.add(Transaction(lawd_cd="43113", property_type="apartment", deal_type="trade",
                           complex_name="통근테스트단지", exclusive_area=84.9, floor=5,
                           contract_date=date.today(), deal_amount=amt,
                           source="TEST", dedup_key=f"ct{i}"))   # complex_id 는 의도적으로 미설정
    db.commit()

    from app.services import commute
    r = commute.search_by_commute(db, dest_id=901, mode="car", max_minutes=60)
    row = next(x for x in r["results"] if x["name"] == "통근테스트단지")
    assert row["price"] == 32000        # 중앙값 — FK 미설정이어도 붙어야 함


def test_search_excludes_no_price(db):
    """시세 표본 없는 단지는 통근 결과에서 제외(v1.278) — 제외 수는 excluded_no_price 로 명시."""
    from app.services import commute
    from app.models import CommuteDestination, Complex
    dest = CommuteDestination(key="t_job", name="테스트직장", category="job",
                              lat=36.64, lng=127.44, is_active=True)
    db.add(dest)
    # 가격 있는 단지(거래 시드)와 없는 단지
    db.add(Complex(name="가격있는단지", lawd_cd="43113", property_type="apartment",
                   lat=36.641, lng=127.441))
    db.add(Complex(name="가격없는단지", lawd_cd="43113", property_type="apartment",
                   lat=36.642, lng=127.442))
    from app.models import Transaction
    from datetime import date
    db.add(Transaction(lawd_cd="43113", property_type="apartment", deal_type="trade",
                       complex_name="가격있는단지", exclusive_area=84.9,
                       contract_date=date(2026, 6, 1), deal_amount=30000,
                       source="TEST", dedup_key="cmt-p1"))
    db.commit()
    j = commute.search_by_commute(db, dest.id, "car", 60)
    names = [r["name"] for r in j["results"]]
    assert "가격있는단지" in names
    assert "가격없는단지" not in names
    assert j["excluded_no_price"] >= 1
