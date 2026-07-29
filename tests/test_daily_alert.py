"""일간 실거래 알림 — 신규 적재분만·빈 소식 금지·하루 1회 멱등(왜곡 없음)."""
from datetime import date

from app.models import Account, DeviceLink, Favorite, Notification, Transaction, UserPref
from app.services import appmeta, daily_alert


def _tx(name, amount, key, lawd="43113", sample=False, canceled=False):
    return Transaction(lawd_cd=lawd, property_type="apartment", deal_type="trade",
                       complex_name=name, exclusive_area=84.9, floor=5,
                       contract_date=date(2026, 7, 1), deal_amount=amount,
                       source="TEST", dedup_key=key, is_sample=sample, is_canceled=canceled)


def _account(db, device="dev-1"):
    a = Account(provider="test", provider_uid=device, nickname="테스터")
    db.add(a); db.flush()
    db.add(DeviceLink(device_id=device, account_id=a.id))
    return a


def test_notifies_only_new_rows_for_watched(db):
    a = _account(db)
    db.add(Favorite(device_id="dev-1", target_type="complex", target_id="관심단지",
                    name="관심단지", meta={"lawd_cd": "43113"}))
    db.add(_tx("관심단지", 30000, "old1"))       # 커서 이전(기존 데이터)
    db.commit()
    daily_alert.run(db, force=True)              # 커서를 현재까지 올림(첫 실행)
    db.query(Notification).delete(); db.commit()

    db.add(_tx("관심단지", 32000, "new1"))       # 신규 적재
    db.add(_tx("무관단지", 99000, "new2"))       # 관심 아님 → 무시
    db.commit()
    r = daily_alert.run(db, force=True)
    assert r["accounts"] == 1 and r["notifications"] == 1
    n = db.query(Notification).filter(Notification.account_id == a.id).one()
    assert "관심단지" in n.message and "무관단지" not in n.message
    assert n.type == "transaction"


def test_no_notification_when_no_new_trades(db):
    _account(db)
    db.add(Favorite(device_id="dev-1", target_type="complex", target_id="관심단지",
                    name="관심단지", meta={"lawd_cd": "43113"}))
    db.commit()
    r = daily_alert.run(db, force=True)
    assert r["notifications"] == 0               # 빈 소식 스팸 금지


def test_sample_and_canceled_excluded(db):
    _account(db)
    db.add(Favorite(device_id="dev-1", target_type="complex", target_id="관심단지",
                    name="관심단지", meta={"lawd_cd": "43113"}))
    db.commit(); daily_alert.run(db, force=True)
    db.add(_tx("관심단지", 31000, "s1", sample=True))
    db.add(_tx("관심단지", 31000, "c1", canceled=True))
    db.commit()
    assert daily_alert.run(db, force=True)["notifications"] == 0


def test_my_home_included_and_first(db):
    a = _account(db)
    db.add(UserPref(device_id="dev-1", data={"my_home": {"complex_name": "우리집단지",
                                                         "lawd_cd": "43113"}}))
    db.commit(); daily_alert.run(db, force=True)
    db.add(_tx("우리집단지", 45000, "h1"))
    db.commit()
    r = daily_alert.run(db, force=True)
    assert r["notifications"] == 1
    msg = db.query(Notification).filter(Notification.account_id == a.id).one().message
    assert "🏠" in msg and "우리집단지" in msg


def test_daily_idempotent(db):
    _account(db)
    db.add(Favorite(device_id="dev-1", target_type="complex", target_id="관심단지",
                    name="관심단지", meta={"lawd_cd": "43113"}))
    db.commit(); daily_alert.run(db, force=True)
    db.add(_tx("관심단지", 33000, "n9")); db.commit()
    daily_alert.run(db)                          # 오늘 첫 실행 → 발송
    r2 = daily_alert.run(db)                     # 같은 날 재실행 → 스킵
    assert r2.get("skipped") == "already_sent_today"
    assert appmeta.get(db, "last_daily_alert_date") == date.today().isoformat()
