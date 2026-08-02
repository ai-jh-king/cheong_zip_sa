"""대출 계산 로직(순수 함수) — 네트워크/DB 불필요."""
import pytest
from app.services import loan


def test_pmt_zero_rate():
    # 무이자: 월상환 = 원금 / (개월수)
    assert loan.pmt(1200, 0, 1) == pytest.approx(100.0)


def test_pmt_positive_rate_exceeds_zero_rate():
    p = loan.pmt(100000, 6.0, 30)
    assert p > 100000 / (30 * 12)   # 이자가 붙으므로 무이자 분할보다 큼


def test_estimate_simple_mode_is_ltv_bound():
    # 동의 없음/소득 없음 → 간이모드(LTV 한도만)
    r = loan.estimate(price=50000, consent=False)
    assert r["binding"] == "LTV"
    assert r["limit"] <= 50000
    assert r["needed_cash"] == max(0, 50000 - r["limit"])


def test_estimate_low_income_does_not_exceed_ltv():
    # 소득이 매우 낮으면 DSR 제약으로 한도가 LTV 이하
    simple = loan.estimate(price=50000, consent=False)
    poor = loan.estimate(price=50000, consent=True, annual_income=1000,
                         existing_annual_payment=0)
    assert poor["limit"] <= simple["limit"]
    assert poor["binding"] in ("LTV", "DSR")


def test_estimate_returns_products_list():
    r = loan.estimate(price=50000, consent=False)
    assert isinstance(r.get("products"), list)


# ---------- v1.253: 시장 금리 요약 · 금리 스트레스 ----------
def test_market_rate_only_from_real_products():
    from app.services import loan as L
    assert L.market_rate(None) is None
    assert L.market_rate([{"kind": "정책", "rate_min": 3, "rate_max": 4}]) is None   # 정책은 시장금리 아님
    assert L.market_rate([{"kind": "은행", "rate_min": 3.9, "rate_max": 5.2,
                           "is_sample": True}]) is None                              # 예시는 제외(왜곡 방지)
    mk = L.market_rate([{"kind": "은행", "rate_min": 3.9, "rate_max": 5.2, "as_of": "2026-08"},
                        {"kind": "은행", "rate_min": 4.1, "rate_max": 5.6}])
    assert mk["min"] == 3.9 and mk["max"] == 5.6 and mk["count"] == 2
    assert 3.9 <= mk["typical"] <= 5.6 and mk["as_of"] == "2026-08"


def test_stress_test_monotonic():
    from app.services import loan as L
    s = L.stress_test(30000, 4.0, 30)
    assert [x["delta"] for x in s] == [0.0, 1.0, 2.0]
    assert s[0]["diff"] == 0
    assert s[1]["monthly"] > s[0]["monthly"] and s[2]["monthly"] > s[1]["monthly"]
    assert s[1]["rate_pct"] == 5.0 and s[2]["rate_pct"] == 6.0
