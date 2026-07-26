"""관심단지 주간 다이제스트 — 발송 조건·멱등·빈 소식 미발송(왜곡/스팸 없음)."""
from datetime import date, timedelta

from app.models import Favorite, DeviceLink, Notification, Transaction
from app.services import weekly_digest


def _tx(name, amt, key, d, lawd="43113"):
    return Transaction(lawd_cd=lawd, property_type="apartment", deal_type="trade",
                       complex_name=name, exclusive_area=84.9, floor=5,
                       contract_date=d, deal_amount=amt, source="TEST",
                       dedup_key=key, is_sample=False)


def _fav(db, acct=1, dev="dev-1", name="다이제스트단지", lawd="43113"):
    db.add(DeviceLink(device_id=dev, account_id=acct))
    db.add(Favorite(device_id=dev, target_type="complex",
                    target_id=f"{name}__{lawd}__apartment", name=name,
                    meta={"lawd_cd": lawd, "complex_name": name}))


def test_digest_creates_notification_and_marks_week(db):
    today = date(2026, 7, 27)                       # 월요일
    _fav(db)
    db.add(_tx("다이제스트단지", 35000, "wd1", today - timedelta(days=2)))
    db.commit()
    res = weekly_digest.run(db, today=today)
    assert res["notifications"] == 1
    n = db.query(Notification).filter(Notification.type == "digest").one()
    assert "다이제스트단지 1건" in n.message and "3.5억" in n.message
    # 같은 주 재실행 → 멱등 skip
    assert weekly_digest.run(db, today=today) == {"skipped": "already_sent"}


def test_digest_skips_when_no_weekly_trades(db):
    """지난주 거래 0건이면 발송하지 않는다(빈 소식 스팸 금지)."""
    today = date(2026, 7, 27)
    _fav(db)
    db.add(_tx("다이제스트단지", 35000, "wd2", today - timedelta(days=30)))   # 오래된 거래만
    db.commit()
    res = weekly_digest.run(db, today=today)
    assert res["notifications"] == 0
    assert db.query(Notification).count() == 0


def test_digest_not_monday_skips(db):
    _fav(db)
    db.commit()
    assert weekly_digest.run(db, today=date(2026, 7, 28)) == {"skipped": "not_monday"}


def test_digest_ignores_unlinked_device(db):
    """계정 미연결(device만) 관심단지는 대상 아님(푸시/알림함 수신자 없음)."""
    today = date(2026, 7, 27)
    db.add(Favorite(device_id="anon-dev", target_type="complex",
                    target_id="X__43113__apartment", name="X", meta={"lawd_cd": "43113"}))
    db.add(_tx("X", 30000, "wd3", today - timedelta(days=1)))
    db.commit()
    res = weekly_digest.run(db, today=today)
    assert res["notifications"] == 0
