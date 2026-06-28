"""취득세·중개보수·총비용 로직(순수 함수)."""
from app.services import costs


def test_acquisition_rate_is_monotonic_nondecreasing():
    assert costs.acquisition_rate(50000) <= costs.acquisition_rate(800000)


def test_broker_fee_monotonic_and_positive():
    low, high = costs.broker_fee(30000), costs.broker_fee(100000)
    assert 0 < low <= high


def test_purchase_costs_total_covers_tax():
    c = costs.purchase_costs(50000)
    for k in ("total", "acquisition_tax", "broker_fee", "tax_total"):
        assert k in c
    assert c["total"] >= c["tax_total"] > 0
