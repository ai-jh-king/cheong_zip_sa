"""법적 고지 — 버전·문서 제공·동의 이력 기록/확인."""
from app.api.legal import PRIVACY_VERSION
from app.models import Consent


def test_versions(client):
    j = client.get("/legal/version").json()
    assert "privacy" in j and "terms" in j


def test_get_privacy_doc(client):
    r = client.get("/legal/privacy")
    assert r.status_code == 200
    j = r.json()
    assert j["version"] == PRIVACY_VERSION
    assert "개인정보처리방침" in j["content"]
    # 실제 처리 방식이 정확히 반영됐는지(서버 미저장)
    assert "저장하지 않" in j["content"]


def test_unknown_doc_404(client):
    assert client.get("/legal/unknown").status_code == 404


def test_consent_record_and_status(client, db):
    # 동의 전: 미동의
    s0 = client.get("/legal/consent/status", params={"device_id": "dev1", "kind": "privacy_loan"}).json()
    assert s0["consented"] is False
    # 동의 기록
    r = client.post("/legal/consent", json={"device_id": "dev1", "kind": "privacy_loan"})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert db.query(Consent).filter(Consent.owner == "dev1").count() == 1
    # 동의 후: 현재 버전 동의됨
    s1 = client.get("/legal/consent/status", params={"device_id": "dev1", "kind": "privacy_loan"}).json()
    assert s1["consented"] is True
    assert s1["version"] == PRIVACY_VERSION


def test_consent_requires_owner(client):
    # device_id 없고 로그인도 없으면 400
    assert client.post("/legal/consent", json={"kind": "privacy_loan"}).status_code == 400
