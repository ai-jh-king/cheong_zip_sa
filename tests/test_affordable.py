"""예산 기반 단지 매칭 — 상한 산출·단지 필터·API."""
from datetime import date
from app.models import Transaction
from app.services import loan, stats
from app.core import cache
from app.sources.molit.normalize import make_dedup_key, make_identity_key


def _tx(db, *, name, amount, lawd="43111", cdate="2026-05-01", floor=5, area=84.9):
    r = {"lawd_cd": lawd, "property_type": "apartment", "deal_type": "trade",
         "complex_name": name, "dong_name": "율량동", "exclusive_area": area, "floor": floor,
         "build_year": 2018, "contract_date": date.fromisoformat(cdate),
         "deal_amount": amount, "deposit": None, "monthly_rent": None, "source": "TEST",
         "is_sample": False, "raw_payload": None, "is_canceled": False, "canceled_date": None}
    r["dedup_key"] = make_dedup_key(r); r["identity_key"] = make_identity_key(r)
    db.add(Transaction(**r))


def test_max_affordable_boundary():
    cash = 20000  # 2억
    budget = loan.max_affordable_price(cash, consent=False)
    assert budget > 0
    # 경계: 예산에선 필요현금 ≤ 보유, 그 위로 크게 가면 초과
    assert loan.estimate(price=budget, consent=False, self_capital=cash)["total_cash_needed"] <= cash
    assert loan.estimate(price=budget + 8000, consent=False, self_capital=cash)["total_cash_needed"] > cash


def test_affordable_complexes_filter(db):
    _tx(db, name="싼단지", amount=30000)
    _tx(db, name="중간단지", amount=55000)
    _tx(db, name="비싼단지", amount=90000)
    db.commit(); cache.bump_data_version()
    out = stats.affordable_complexes(db, max_price=60000, property_type="apartment")
    names = [c["name"] for c in out]
    assert "싼단지" in names and "중간단지" in names
    assert "비싼단지" not in names              # 예산 초과 제외
    assert out[0]["median_price"] >= out[-1]["median_price"]  # 비싼 순


def test_affordable_api(client, db):
    _tx(db, name="API싼단지", amount=25000); db.commit(); cache.bump_data_version()
    r = client.post("/loan/affordable", json={"self_capital": 30000, "consent": False})
    assert r.status_code == 200
    body = r.json()
    assert body["budget_max"] > 0
    assert all(it["median_price"] <= body["budget_max"] for it in body["items"])
