"""보유비용(재산세 법정계산)·전세대출 — 왜곡 없음(공시가 없으면 계산 안 함·예시 금리 금지)."""
from app.services import holding, rentloan


def test_property_tax_requires_official_price():
    assert holding.property_tax(None) is None          # 시세로 추정하지 않음
    assert holding.property_tax(0) is None


def test_property_tax_one_house_special_rate():
    # 공시가 2억, 1세대 1주택 → 공정비율 43%, 과세표준 8,600만 → 특례세율 구간(6천~1.5억)
    r = holding.property_tax(20000, one_house=True)
    assert r["fair_ratio"] == 0.43 and r["tax_base"] == 8600
    assert r["rate_table"] == "1세대 1주택 특례"
    # 3만 + (8600-6000)*0.001 = 3 + 2.6 = 5.6만원
    assert abs(r["tax"] - 6) <= 1
    assert r["edu_tax"] == round(r["tax"] * 0.2)
    assert r["total"] >= r["tax"] and r["monthly"] == round(r["total"] / 12)


def test_property_tax_standard_when_multi_house():
    r1 = holding.property_tax(20000, one_house=True)
    r2 = holding.property_tax(20000, one_house=False)
    assert r2["rate_table"] == "표준" and r2["fair_ratio"] == 0.60
    assert r2["total"] > r1["total"]                    # 다주택이 더 큼(특례 미적용)


def test_property_tax_over_9eok_no_special():
    r = holding.property_tax(100000, one_house=True)    # 공시가 10억 → 특례 배제
    assert r["rate_table"] == "표준"


def test_monthly_burden_only_sums_known():
    r = holding.monthly_burden(loan_monthly=120, official_price=None, maintenance_fee=None)
    assert r["total"] == 120 and r["property_tax"] is None
    assert any("공시가격" in m for m in r["missing"])
    assert any("관리비" in m for m in r["missing"])
    r2 = holding.monthly_burden(loan_monthly=120, official_price=20000, maintenance_fee=15)
    assert r2["total"] == 120 + r2["property_tax"]["monthly"] + 15
    assert len(r2["parts"]) == 3 and not r2["missing"]


def test_rent_loan_structure():
    r = rentloan.estimate(deposit=20000, cash=5000, income=4000, homeless=True)
    assert r["max_by_deposit"] == 16000                 # 보증금 80%
    assert r["need"] == 15000 and r["loan_amount"] == 15000
    assert r["shortfall"] == 0
    assert r["rate_pct"] is None and r["monthly_interest"] is None   # 미연동 시 금리 없음
    assert r["policy"]["items"] and r["disclaimer"]


def test_rent_loan_shortfall_and_interest():
    r = rentloan.estimate(deposit=30000, cash=1000, rate_pct=4.0)
    assert r["need"] == 29000 and r["max_by_deposit"] == 24000
    assert r["loan_amount"] == 24000 and r["shortfall"] == 5000      # 한도로도 부족
    assert r["monthly_interest"] == round(24000 * 0.04 / 12)


def test_rent_loan_api(client, db):
    j = client.post("/loan/rent", json={"deposit": 20000, "cash": 5000}).json()
    assert j["max_by_deposit"] == 16000 and "disclaimer" in j
    h = client.post("/loan/holding-cost", json={"loan_monthly": 100}).json()
    assert h["total"] == 100
