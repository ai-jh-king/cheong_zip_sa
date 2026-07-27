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


def test_rent_gap_signal_bands():
    """전세가율 해석 신호: 밴드 경계·None 처리. 가격 예측이 아니라 참고 신호(왜곡 없음)."""
    assert stats.rent_gap_signal(None) is None
    hi = stats.rent_gap_signal(92.0)
    assert hi["level"] == "high" and hi["jeonse_ratio"] == 92.0
    assert "역전세" in hi["note"] or "깡통" in hi["note"]      # 세입자 주의 맥락
    assert stats.rent_gap_signal(85.0)["level"] == "high"      # 경계 포함
    assert stats.rent_gap_signal(80.0)["level"] == "elevated"
    assert stats.rent_gap_signal(65.0)["level"] == "normal"
    assert stats.rent_gap_signal(40.0)["level"] == "low"
    # 단정 표현이 없어야 함(가격 하락/상승 확정 금지)
    for jr in (95.0, 80.0, 65.0, 40.0):
        note = stats.rent_gap_signal(jr)["note"]
        assert "반드시" not in note and "확정" not in note


# ---------- 지도 마커: 같은 구 동명(同名) 단지 분리(v1.224) ----------
def _tx_dong(name, dong, amount, key, lawd="43113"):
    return Transaction(lawd_cd=lawd, property_type="apartment", deal_type="trade",
                       complex_name=name, dong_name=dong, exclusive_area=84.9, floor=5,
                       contract_date=date(2026, 5, 1), deal_amount=amount,
                       source="TEST", dedup_key=key)


def test_map_markers_splits_same_name_across_dongs(db):
    """가경동 '대원'과 복대동 '대원'은 다른 단지 — 마커 2개, 좌표·중앙값 미혼합."""
    from app.models import Complex
    db.add(Complex(name="대원", lawd_cd="43113", property_type="apartment",
                   dong="가경동", lat=36.63, lng=127.42))
    db.add(Complex(name="대원", lawd_cd="43113", property_type="apartment",
                   dong="복대동", lat=36.65, lng=127.44))
    for i, a in enumerate([30000, 31000, 32000]):
        db.add(_tx_dong("대원", "가경동", a, f"ga{i}"))
    for i, a in enumerate([50000, 51000, 52000]):
        db.add(_tx_dong("대원", "복대동", a, f"bok{i}"))
    db.commit(); cache.bump_data_version()
    ms = [m for m in stats.map_markers(db, "trade", "apartment")["markers"]
          if m["complex_name"] == "대원"]
    assert len(ms) == 2
    by_dong = {m["dong"]: m for m in ms}
    assert by_dong["가경동"]["lat"] == 36.63 and by_dong["복대동"]["lat"] == 36.65
    assert by_dong["가경동"]["median_amount"] == 31000    # 복대동 5억대와 섞이지 않음
    assert by_dong["복대동"]["median_amount"] == 51000


def test_map_markers_ambiguous_legacy_coord_excluded(db):
    """복수 동에 걸친 이름인데 좌표가 레거시(dong=None) 1개뿐 → 어느 단지 좌표인지
    알 수 없으므로 지도에서 제외(좌표 미확인=날조 방지). 동이 유일하면 레거시 좌표 사용."""
    from app.models import Complex
    db.add(Complex(name="세원", lawd_cd="43113", property_type="apartment",
                   dong=None, lat=36.64, lng=127.43))           # 모호 — 제외돼야
    db.add(Complex(name="유일", lawd_cd="43113", property_type="apartment",
                   dong=None, lat=36.66, lng=127.45))           # 동 유일 — 사용돼야
    for i, a in enumerate([30000, 31000, 32000]):
        db.add(_tx_dong("세원", "복대동", a, f"se{i}"))
    for i, a in enumerate([40000, 41000, 42000]):
        db.add(_tx_dong("세원", "봉명동", a, f"sb{i}"))
    for i, a in enumerate([20000, 21000, 22000]):
        db.add(_tx_dong("유일", "운천동", a, f"u{i}"))
    db.commit(); cache.bump_data_version()
    ms = stats.map_markers(db, "trade", "apartment")["markers"]
    assert not [m for m in ms if m["complex_name"] == "세원"]
    u = [m for m in ms if m["complex_name"] == "유일"]
    assert len(u) == 1 and u[0]["dong"] == "운천동" and u[0]["lat"] == 36.66
