"""등록 매물 — 조회수 원자 집계(소유자 제외) + 목록에서 연락처 숨김(순번 스크래핑 방지)."""
from datetime import datetime
from app.models import Listing


def _make_listing(db):
    x = Listing(device_id="owner1", title="테스트 매물입니다", deal_type="trade",
                property_type="apartment", lawd_cd="43113", price=30000,
                agent_phone="010-1234-5678", agent_address="청주시 어딘가",
                status="active", created_at=datetime.utcnow())
    db.add(x)
    db.commit()
    db.refresh(x)
    return x.id


def test_listing_views_atomic_and_owner_excluded(client, db):
    lid = _make_listing(db)
    client.get(f"/listings/{lid}?device_id=other")
    v = client.get(f"/listings/{lid}?device_id=other").json()
    assert v["views"] == 2                       # 외부 조회 2회 원자 집계
    client.get(f"/listings/{lid}?device_id=owner1")   # 소유자 조회는 미집계
    v2 = client.get(f"/listings/{lid}?device_id=other").json()
    assert v2["views"] == 3                       # 소유자 조회가 카운트되지 않음


def test_listing_phone_hidden_in_list_shown_in_detail(client, db):
    lid = _make_listing(db)
    detail = client.get(f"/listings/{lid}?device_id=x").json()
    assert detail.get("agent_phone") == "010-1234-5678"   # 상세엔 노출(연락 목적)
    items = client.get("/listings", params={"gu": "43113"}).json()["items"]
    row = next(r for r in items if r["id"] == lid)
    assert "agent_phone" not in row and "agent_address" not in row   # 목록엔 숨김
