"""매물 문의(리드) — 생성·동의·소유자 열람·상태변경·마스킹(billing OFF 기본).

격리: conftest 가 throwaway SQLite + RATE_LIMIT_ENABLED=false + feature_billing 미설정(OFF).
"""
from app.models import Listing


def _listing(db, *, device_id="ownerdev", title="테스트매물", status="active"):
    x = Listing(device_id=device_id, title=title, deal_type="trade",
                property_type="apartment", lawd_cd="43111", dong_name="율량동", status=status)
    db.add(x); db.commit(); db.refresh(x)
    return x


def test_create_requires_consent(client, db):
    x = _listing(db)
    r = client.post("/inquiries", json={"listing_id": x.id, "contact": "010-1234-5678",
                                        "message": "문의합니다", "consent": False})
    assert r.status_code == 400  # 동의 없으면 생성 거부


def test_create_and_owner_reads_contact(client, db):
    x = _listing(db, device_id="ownerdev")
    r = client.post("/inquiries", json={"listing_id": x.id, "device_id": "askerdev",
                                        "name": "홍길동", "contact": "010-1111-2222",
                                        "message": "방문 가능한가요", "consent": True})
    assert r.status_code == 200 and r.json()["ok"] is True
    r2 = client.get("/inquiries", params={"device_id": "ownerdev"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["total"] == 1 and body["new"] == 1
    assert body["items"][0]["contact"] == "010-1111-2222"   # 소유자에겐 연락처 노출
    assert body["items"][0]["locked"] is False              # billing OFF → 마스킹 없음


def test_create_on_hidden_listing_404(client, db):
    x = _listing(db, status="hidden")
    r = client.post("/inquiries", json={"listing_id": x.id, "contact": "010-0000-0000",
                                        "message": "x", "consent": True})
    assert r.status_code == 404


def test_create_on_missing_listing_404(client, db):
    r = client.post("/inquiries", json={"listing_id": 999999, "contact": "010-0",
                                        "message": "x", "consent": True})
    assert r.status_code == 404


def test_non_owner_cannot_read(client, db):
    x = _listing(db, device_id="ownerdev")
    client.post("/inquiries", json={"listing_id": x.id, "contact": "010-1111-2222",
                                    "message": "hi", "consent": True})
    r = client.get("/inquiries", params={"device_id": "otherdev"})
    assert r.status_code == 200
    assert r.json()["total"] == 0           # 타인은 본인 매물 문의만 → 0건


def test_status_update_owner_only(client, db):
    x = _listing(db, device_id="ownerdev")
    client.post("/inquiries", json={"listing_id": x.id, "contact": "010-1",
                                    "message": "hi", "consent": True})
    iid = client.get("/inquiries", params={"device_id": "ownerdev"}).json()["items"][0]["id"]
    r = client.post(f"/inquiries/{iid}/status", params={"device_id": "otherdev"},
                    json={"status": "read"})
    assert r.status_code == 403             # 타인 변경 불가
    r2 = client.post(f"/inquiries/{iid}/status", params={"device_id": "ownerdev"},
                     json={"status": "contacted"})
    assert r2.status_code == 200 and r2.json()["status"] == "contacted"


def test_summary_counts(client, db):
    x = _listing(db, device_id="ownerdev")
    for i in range(3):
        client.post("/inquiries", json={"listing_id": x.id, "contact": f"010-{i}",
                                        "message": "hi", "consent": True})
    r = client.get("/inquiries/summary", params={"device_id": "ownerdev"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3 and body["new"] == 3
    assert body["by_listing"][str(x.id)]["total"] == 3


def test_read_requires_identity(client, db):
    r = client.get("/inquiries")
    assert r.status_code == 401             # 로그인/device_id 없으면 거부
