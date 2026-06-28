"""단지 비교 — compare_one 지표 + /compare API."""
from datetime import date
from app.models import Transaction
from app.services import stats
from app.core import cache
from app.sources.molit.normalize import make_dedup_key, make_identity_key


def _tx(db, *, name, amount, deal="trade", area=84.9, deposit=None, lawd="43111", cdate="2026-05-01", floor=5):
    r = {"lawd_cd": lawd, "property_type": "apartment", "deal_type": deal,
         "complex_name": name, "dong_name": "율량동", "exclusive_area": area, "floor": floor,
         "build_year": 2018, "contract_date": date.fromisoformat(cdate),
         "deal_amount": amount, "deposit": deposit, "monthly_rent": None, "source": "TEST",
         "is_sample": False, "raw_payload": None, "is_canceled": False, "canceled_date": None}
    r["dedup_key"] = make_dedup_key(r)
    r["identity_key"] = make_identity_key(r)
    db.add(Transaction(**r))


def test_compare_one_metrics(db):
    _tx(db, name="비교단지", amount=50000, cdate="2026-04-01")
    _tx(db, name="비교단지", amount=60000, cdate="2026-05-01")          # 최신
    _tx(db, name="비교단지", amount=30000, deal="jeonse", deposit=30000)  # 전세
    db.commit(); cache.bump_data_version()
    m = stats.compare_one(db, "비교단지", "43111", "apartment")
    assert m["found"] is True
    assert m["latest_amount"] == 60000
    assert m["median_amount"] == 60000      # [50000,60000] 중앙(상위)
    assert m["trade_count"] == 2
    assert m["jeonse_ratio"] == 50          # 30000/60000*100
    assert m["ppm_median"] is not None
    assert m["build_year"] == 2018


def test_compare_one_not_found(db):
    m = stats.compare_one(db, "없는단지", "43111", "apartment")
    assert m["found"] is False


def test_compare_api(client, db):
    _tx(db, name="API단지", amount=40000); db.commit(); cache.bump_data_version()
    r = client.post("/compare", json={"items": [
        {"name": "API단지", "lawd_cd": "43111", "property_type": "apartment"},
        {"name": "없음", "lawd_cd": "43111", "property_type": "apartment"}]})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["found"] is True
    assert body["items"][1]["found"] is False
