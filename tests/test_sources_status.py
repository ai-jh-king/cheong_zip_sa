"""소스 실연동 게이트 — 프로브 전엔 숨김(보수적), 프로브 후 실제 상태 반영."""
from app.services import sources_status


def test_get_defaults_hidden_before_probe(db):
    v = sources_status.get(db)
    assert v["subscription"] is False and v["bank_rates"] is False and v["places"] is False


def test_probe_reflects_sources(db, monkeypatch):
    monkeypatch.setattr("app.sources.applyhome.fetch_subscriptions", lambda limit=1: [{"name": "x"}])
    monkeypatch.setattr("app.sources.finlife.fetch_loan_products", lambda limit=1: None)
    v = sources_status.probe(db)
    assert v["subscription"] is True          # 실데이터 있음 → 노출
    assert v["bank_rates"] is False           # 미연동 → 숨김
    assert v["places"] is False               # 시설 미적재
    assert sources_status.get(db)["subscription"] is True   # app_meta 에 저장돼 재조회 가능


def test_probe_survives_connector_error(db, monkeypatch):
    def boom(limit=1):
        raise RuntimeError("network")
    monkeypatch.setattr("app.sources.applyhome.fetch_subscriptions", boom)
    v = sources_status.probe(db)
    assert v["subscription"] is False         # 예외는 False 로만 반영(전체 실패 아님)


def test_config_exposes_live(client, db):
    j = client.get("/config").json()
    assert "live" in j and set(["subscription", "bank_rates", "places"]) <= set(j["live"])
