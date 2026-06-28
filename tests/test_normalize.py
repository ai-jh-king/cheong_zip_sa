"""실거래 정규화 키 규약 — 정정(금액변경)/해제 매칭의 토대."""
from app.sources.molit import normalize


def _norm(amount):
    return {
        "property_type": "apartment", "deal_type": "trade", "lawd_cd": "43111",
        "complex_name": "샘플리버뷰", "exclusive_area": 84.9, "floor": 10,
        "contract_date": "2026-05-01", "dong_name": "율량동",
        "deal_amount": amount, "deposit": None, "monthly_rent": None,
    }


def test_identity_ignores_amount_but_dedup_does_not():
    a, b = _norm(50000), _norm(52000)   # 정정으로 금액만 바뀐 동일 계약
    assert normalize.make_identity_key(a) == normalize.make_identity_key(b)
    assert normalize.make_dedup_key(a) != normalize.make_dedup_key(b)


def test_dedup_key_stable_for_same_input():
    assert normalize.make_dedup_key(_norm(50000)) == normalize.make_dedup_key(_norm(50000))
