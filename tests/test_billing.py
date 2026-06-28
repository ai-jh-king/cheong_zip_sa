"""결제/구독 — feature_billing OFF가 기본일 때 현재와 동일해야 함(핵심 불변식).

conftest 는 feature_billing 을 설정하지 않으므로 기본 False.
ON 상태의 mock 결제 전 흐름은 운영 환경 토글이 필요해 수동 검증(TESTING.md L). 여기서는
'꺼져 있으면 결제가 노출/동작하지 않는다'는 안전 불변식과 플랜 정의 구조를 고정한다.
"""
from app.services import billing


def test_plans_disabled_by_default(client):
    r = client.get("/billing/plans")
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert r.json()["plans"] == []


def test_me_disabled_by_default(client):
    r = client.get("/billing/me")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False and body["premium"] is False
    assert body["subscription"] is None


def test_checkout_404_when_off(client):
    r = client.post("/billing/checkout", json={"plan": "agent_pro"})
    assert r.status_code == 404


def test_confirm_404_when_off(client):
    r = client.post("/billing/confirm", json={"plan": "agent_pro", "token": "mock_x"})
    assert r.status_code == 404


def test_cancel_404_when_off(client):
    r = client.post("/billing/cancel")
    assert r.status_code == 404


def test_plan_structure():
    assert "agent_pro" in billing.PLANS
    p = billing.PLANS["agent_pro"]
    assert isinstance(p["price"], int) and p["price"] > 0
    assert p["period_days"] > 0
    assert isinstance(p["perks"], list) and p["perks"]


def test_create_checkout_mock_token():
    # provider=mock(기본)일 때 confirm_token 발급(서비스 단위)
    class _Acc:  # 최소 더블
        id = 1
        plan = "free"
    out = billing.create_checkout("agent_pro", _Acc())
    assert out["provider"] == "mock" and out["mode"] == "mock"
    assert out["confirm_token"].startswith("mock_")
    assert out["amount"] == billing.PLANS["agent_pro"]["price"]
