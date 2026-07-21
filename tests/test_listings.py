"""등록 매물 — 조회수 원자 집계(소유자 제외) + 목록에서 연락처 숨김(순번 스크래핑 방지)
 + 매물의 '말릴 수 있는' 신호(실거래 대비·전세가율)."""
from datetime import datetime, date
from app.models import Listing, Transaction
from app.services import pricecheck as pc


def _trade(name, amt, key, area=84.9):
    return Transaction(lawd_cd="43113", property_type="apartment", deal_type="trade",
                       complex_name=name, exclusive_area=area, contract_date=date(2026, 5, 1),
                       deal_amount=amt, source="TEST", dedup_key=key)


def test_listing_signal_trade_vs_market(db):
    for i, a in enumerate([50000, 52000, 54000]):
        db.add(_trade("신호단지", a, f"s{i}"))
    db.commit()
    sig = pc.listing_signal(db, "trade", "신호단지", "43113", 44000, None, 84.9, "apartment")
    assert sig["kind"] == "trade" and sig["median"] == 52000
    assert sig["diff_pct"] == round((44000 - 52000) / 52000 * 100, 1) and sig["bargain"] is True
    assert "단정" in sig["disclaimer"]
    assert pc.listing_signal(db, "trade", "없는단지", "43113", 44000, None, 84.9) is None   # 미매칭 숨김
    assert pc.listing_signal(db, "trade", "신호단지", "43113", 44000, None, 20.0) is None    # 다른 평형=표본부족


def test_listing_signal_jeonse_ratio(db):
    for i, a in enumerate([50000, 52000, 54000]):
        db.add(_trade("전세신호", a, f"j{i}"))
    db.commit()
    sig = pc.listing_signal(db, "jeonse", "전세신호", "43113", None, 46000, 84.9, "apartment")
    assert sig["kind"] == "jeonse" and sig["jeonse_ratio"] == round(46000 / 52000 * 100, 1)
    assert sig["sale_median"] == 52000 and "단정" in sig["disclaimer"]


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
