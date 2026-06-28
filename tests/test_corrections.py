"""실거래 정정·해제 반영(⑥) — 멱등/정정 갱신/해제 표시/모호 보존."""
from datetime import date
from app.models import Transaction
from app.pipeline.collect import upsert_transactions
from app.sources.molit.normalize import make_dedup_key, make_identity_key
from app.services import stats
from app.core import cache


def nrow(amount, *, canceled=False, name="샘플", floor=5, area=84.9, lawd="43111", cdate="2026-05-01"):
    r = {"lawd_cd": lawd, "property_type": "apartment", "deal_type": "trade",
         "complex_name": name, "dong_name": "율량동", "exclusive_area": area, "floor": floor,
         "build_year": 2018, "contract_date": date.fromisoformat(cdate),
         "deal_amount": amount, "deposit": None, "monthly_rent": None, "source": "TEST",
         "is_sample": False, "raw_payload": None, "is_canceled": canceled, "canceled_date": None}
    r["dedup_key"] = make_dedup_key(r)
    r["identity_key"] = make_identity_key(r)
    return r


def test_insert_then_idempotent(db):
    assert upsert_transactions(db, [nrow(50000)])["inserted"] == 1
    # 동일 행 재적재 → skip
    res = upsert_transactions(db, [nrow(50000)])
    assert res["inserted"] == 0
    assert db.query(Transaction).count() == 1


def test_correction_updates_same_row(db):
    upsert_transactions(db, [nrow(50000)])
    res = upsert_transactions(db, [nrow(52000)])   # 같은 계약, 금액만 정정
    assert res["corrected"] == 1 and res["inserted"] == 0
    rows = db.query(Transaction).all()
    assert len(rows) == 1                            # 중복 생성 안 됨
    assert rows[0].deal_amount == 52000
    assert rows[0].corrected_at is not None


def test_cancellation_marks_and_excludes(db):
    upsert_transactions(db, [nrow(50000)])
    res = upsert_transactions(db, [nrow(50000, canceled=True)])
    assert res["canceled"] == 1
    row = db.query(Transaction).one()
    assert row.is_canceled is True
    # 집계에서 제외
    cache.bump_data_version()
    assert stats.city_summary(db, "apartment")["trade_count"] == 0


def test_ambiguous_two_active_preserved(db):
    # 같은 identity 활성 2건을 직접 적재(모호 상태)
    db.add(Transaction(**nrow(50000)))
    db.add(Transaction(**nrow(51000)))   # 같은 identity, 다른 dedup(금액)
    db.commit()
    res = upsert_transactions(db, [nrow(52000)])   # 모호 → 신규 적재(기존 보존)
    assert res["inserted"] == 1
    assert db.query(Transaction).count() == 3
