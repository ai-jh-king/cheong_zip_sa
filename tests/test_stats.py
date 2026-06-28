"""시세 집계 — 해제분 제외, 평균/건수 정확성."""
from datetime import date
from app.models import Transaction
from app.services import stats
from app.core import cache


def _tx(amount, key, canceled=False):
    return Transaction(lawd_cd="43111", property_type="apartment", deal_type="trade",
                       complex_name="샘플", exclusive_area=84.9, floor=5,
                       contract_date=date(2026, 5, 1), deal_amount=amount,
                       source="TEST", dedup_key=key, is_canceled=canceled)


def test_city_summary_excludes_canceled_and_computes_avg(db):
    for i, amt in enumerate([30000, 40000, 50000]):
        db.add(_tx(amt, f"k{i}"))
    db.add(_tx(999999, "canceled", canceled=True))   # 해제분: 제외돼야
    db.commit()
    cache.bump_data_version()                         # 캐시 무효화 후 재계산

    r = stats.city_summary(db, "apartment")
    assert r["trade_count"] == 3
    assert r["avg_mae"] == 40000                      # (30000+40000+50000)/3


def test_city_summary_insufficient_when_empty(db):
    cache.bump_data_version()
    r = stats.city_summary(db, "apartment")
    assert r["trade_count"] == 0
    assert r["avg_mae"] is None


def test_aggregate_window_excludes_old(db):
    """집계 기본 윈도우(최근 12개월) — 윈도우 밖 거래는 현재 시세에서 제외."""
    from datetime import timedelta
    recent_d = date.today() - timedelta(days=30)    # 윈도우 내
    old_d = date.today() - timedelta(days=400)       # ~13개월 전(윈도우 밖)

    def mk(amt, key, d):
        return Transaction(lawd_cd="43111", property_type="apartment", deal_type="trade",
                           complex_name="윈도우", exclusive_area=84.9, floor=5,
                           contract_date=d, deal_amount=amt, source="TEST",
                           dedup_key=key, is_canceled=False)

    db.add(mk(50000, "w_recent", recent_d))
    db.add(mk(99999, "w_old", old_d))
    db.commit(); cache.bump_data_version()
    r = stats.city_summary(db, "apartment")
    assert r["trade_count"] == 1        # 최근만 집계
    assert r["avg_mae"] == 50000        # 옛 거래(99999) 제외
