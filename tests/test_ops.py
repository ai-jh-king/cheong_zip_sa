"""관측성 — /health(DB 핑)·/status/data(신선도)·app_meta 헬퍼."""
from datetime import date
from app.models import Transaction
from app.services import appmeta


def test_health_db_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["db_ok"] is True
    assert j["status"] == "ok"
    assert "data_version" in j


def test_data_status_shape(client):
    r = client.get("/status/data")
    assert r.status_code == 200
    j = r.json()
    for k in ("total_transactions", "per_gu", "geocode", "stale", "data_version"):
        assert k in j
    assert len(j["per_gu"]) == 4          # 청주 4개 구
    assert j["stale"] is True             # 수집 기록 없음 → stale


def test_data_status_counts_real_only(client, db):
    db.add(Transaction(lawd_cd="43111", property_type="apartment", deal_type="trade",
                       complex_name="A", contract_date=date(2026, 5, 1), deal_amount=30000,
                       source="T", dedup_key="r1"))
    db.add(Transaction(lawd_cd="43111", property_type="apartment", deal_type="trade",
                       complex_name="B", contract_date=date(2026, 4, 1), deal_amount=40000,
                       source="T", dedup_key="s1", is_sample=True))   # 모의 → 제외
    db.commit()
    j = client.get("/status/data").json()
    assert j["total_transactions"] == 1
    assert j["data_as_of"] == "2026-05-01"


def test_appmeta_roundtrip(db):
    appmeta.set(db, "k1", "v1")
    assert appmeta.get(db, "k1") == "v1"
    appmeta.set_json(db, "k2", {"a": 1})
    assert appmeta.get_json(db, "k2") == {"a": 1}
    assert appmeta.get_int(db, "missing", 7) == 7
