"""경량 Row 로더 회귀 — 집계가 전체 ORM 객체 대신 _AGG_COLS(필요 컬럼)만
조회하도록 바꾼 뒤에도 모든 집계 함수가 정상 동작하는지 확인.
컬럼을 하나라도 빠뜨리면 Row 속성 접근에서 AttributeError → 여기서 검출된다.
"""
from datetime import date
from app.models import Transaction
from app.services import stats
from app.core import cache


def _tx(amount=40000, *, deal="trade", deposit=None, rent=None, key="k",
        lawd="43111", name="샘플단지", area=84.9, cdate=date(2026, 5, 1)):
    return Transaction(lawd_cd=lawd, property_type="apartment", deal_type=deal,
                       complex_name=name, dong_name="율량동", exclusive_area=area,
                       floor=5, contract_date=cdate, deal_amount=amount,
                       deposit=deposit, monthly_rent=rent, build_year=2018,
                       source="TEST", dedup_key=key)


def _seed(db):
    db.add(_tx(30000, key="t1"))
    db.add(_tx(50000, key="t2", cdate=date(2026, 4, 1)))
    db.add(_tx(amount=None, deal="jeonse", deposit=28000, key="j1"))
    db.add(_tx(amount=None, deal="wolse", deposit=5000, rent=60, key="w1"))
    db.add(_tx(45000, key="t3", lawd="43112", name="서원단지"))   # 다른 구
    db.commit()
    cache.bump_data_version()


def test_all_aggregations_run_with_lightweight_rows(db):
    """바뀐 로더(_load_window/_rows_where)를 쓰는 함수 전부 호출 → 예외 없이 동작."""
    _seed(db)
    assert stats.city_summary(db, "apartment")["trade_count"] == 3
    assert stats.by_region(db, "apartment") is not None
    assert stats.trend(db, "apartment", 6) is not None
    assert stats.ppm_by_area(db, "apartment") is not None
    assert stats.volume(db, "apartment") is not None
    assert stats.active_regions(db, "all") is not None
    assert stats.complex_movers(db, "apartment", 5) is not None
    assert stats.newly_high(db, "apartment", 5) is not None
    assert stats.top_trades(db, "apartment", 10) is not None
    assert stats.gu_price_ranking(db, "apartment") is not None
    assert stats.recent_trades(db, "apartment", 4) is not None


def test_by_region_values_correct(db):
    """경량 Row 전환 후에도 집계 숫자가 정확한지(왜곡 없음)."""
    _seed(db)
    regions = stats.by_region(db, "apartment")
    sang = next((x for x in regions if x["code"] == "43111"), None)
    assert sang is not None
    assert sang["trade_count"] == 2          # 상당구 매매 2건(30000, 50000)
    assert sang["avg_mae"] == 40000          # 평균 40000


def test_complex_detail_vs_region(db):
    """단지 vs 동네 평단가 포지셔닝 — 같은 평형이면 단지가 구 평균보다 비싸게."""
    from datetime import date
    from app.services import stats as st
    # 대상 단지(비싼): 84㎡ 5억 2건
    db.add(_tx(52000, key="c1", name="프리미엄단지", area=84.0))
    db.add(_tx(52000, key="c2", name="프리미엄단지", area=84.0, cdate=date(2026, 4, 1)))
    # 같은 구 다른 단지(저렴): 84㎡ 4억
    db.add(_tx(40000, key="o1", name="일반단지", area=84.0))
    db.add(_tx(40000, key="o2", name="일반단지", area=84.0, cdate=date(2026, 4, 1)))
    db.commit()
    cache.bump_data_version()
    d = st.complex_detail(db, "프리미엄단지", "43111", "apartment")
    assert d["found"] and d["vs_region"] is not None
    assert d["vs_region"]["pct"] > 0          # 구 평균보다 비쌈
    assert d["vs_region"]["gu"]                 # 구 이름 존재
