"""관심 단지/지역 신규 실거래 알림 — 매칭·수신자·중복방지(커서)."""
from datetime import date, datetime
from app.models import Transaction, Favorite, DeviceLink, Account, Notification
from app.services.notify_transactions import notify_new_transactions


def _tx(amount, key, lawd="43111", name="샘플리버뷰", ptype="apartment", sample=False, canceled=False):
    return Transaction(lawd_cd=lawd, property_type=ptype, deal_type="trade",
                       complex_name=name, exclusive_area=84.9, floor=5,
                       contract_date=date(2026, 5, 1), deal_amount=amount,
                       source="TEST", dedup_key=key, is_sample=sample, is_canceled=canceled)


def _login_fav(db, device="dev1", acct_id=None):
    acc = Account(provider="dev", provider_uid="u1", role="user", nickname="테스터")
    db.add(acc)
    db.flush()
    db.add(DeviceLink(device_id=device, account_id=acc.id))
    db.add(Favorite(device_id=device, target_type="complex",
                    target_id="샘플리버뷰__43111__apartment", name="샘플리버뷰",
                    meta={"lawd_cd": "43111", "property_type": "apartment"}))
    db.commit()
    return acc.id


def test_notifies_logged_in_favorite_owner(db):
    acct = _login_fav(db)
    db.add(_tx(50000, "k1"))
    db.add(_tx(51000, "k2"))   # 같은 단지 2건 → 1개 알림(그룹)
    db.commit()
    res = notify_new_transactions(db)
    assert res["notifications"] == 1
    notes = db.query(Notification).filter(Notification.account_id == acct).all()
    assert len(notes) == 1
    assert notes[0].type == "transaction"
    assert notes[0].complex_name == "샘플리버뷰"
    assert "2건" in (notes[0].message or "")


def test_cursor_prevents_duplicate(db):
    _login_fav(db)
    db.add(_tx(50000, "k1"))
    db.commit()
    assert notify_new_transactions(db)["notifications"] == 1
    # 새 거래 없이 다시 실행 → 추가 알림 없음(커서)
    assert notify_new_transactions(db)["notifications"] == 0


def test_sample_and_canceled_excluded(db):
    _login_fav(db)
    db.add(_tx(50000, "s1", sample=True))      # 모의데이터 제외
    db.add(_tx(50000, "c1", canceled=True))    # 해제분 제외
    db.commit()
    assert notify_new_transactions(db)["notifications"] == 0


def test_anonymous_favorite_not_notified(db):
    # 로그인(DeviceLink) 없는 device 관심등록 → 영속 알림 대상 아님
    db.add(Favorite(device_id="anon", target_type="complex",
                    target_id="샘플리버뷰__43111__apartment", name="샘플리버뷰"))
    db.add(_tx(50000, "k1"))
    db.commit()
    assert notify_new_transactions(db)["notifications"] == 0
