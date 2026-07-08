"""가격 검증 3종 — 판정 없음(사실·백분위·면책)을 검증."""
from datetime import date
from app.models import Transaction
from app.services import pricecheck as pc


def _tx(name, amt, key, area=84.9, d=date(2026, 5, 10), floor=7):
    return Transaction(lawd_cd="43113", property_type="apartment", deal_type="trade",
                       complex_name=name, exclusive_area=area, floor=floor,
                       contract_date=d, deal_amount=amt, source="TEST", dedup_key=key)


def test_quote_check_percentile_and_disclaimer(db):
    for i, a in enumerate([48000, 50000, 52000, 55000, 60000]):
        db.add(_tx("검증단지", a, f"q{i}"))
    db.commit()
    r = pc.quote_check(db, "검증단지", "43113", asking=58000)
    assert r["found"] and r["median"] == 52000
    assert r["diff_pct"] == round((58000-52000)/52000*100, 1)
    assert r["percentile"] == 80            # 5건 중 4건이 58000 이하
    assert "단정" in r["disclaimer"]
    few = pc.quote_check(db, "없는단지", "43113", asking=30000)
    assert few["found"] is False and "부족" not in few.get("disclaimer","단정")  # 면책 항상 포함


def test_bargain_radar_flags_low_trade_with_caution(db):
    for i, a in enumerate([50000, 51000, 52000, 53000]):
        db.add(_tx("레이더단지", a, f"b{i}", d=date(2026, 2, 1)))
    db.add(_tx("레이더단지", 40000, "low1", d=date(2026, 6, 1), floor=1))   # -21%대
    db.commit()
    r = pc.bargain_radar(db, months=3)
    assert r["items"] and r["items"][0]["name"] == "레이더단지"
    assert r["items"][0]["diff_pct"] <= -12
    assert "단정하지" in r["disclaimer"]


def test_gu_context_medians(db):
    for i, a in enumerate([50000, 60000, 70000]):
        db.add(_tx("맥락단지", a, f"g{i}"))
    db.commit()
    r = pc.gu_context(db)
    it = next(x for x in r["items"] if x["lawd_cd"] == "43113")
    assert it["price_median"] == 60000 and it["count"] == 3 and it["ppm_median"] > 0


def test_bargain_radar_includes_coords_when_geocoded(db):
    """급매 항목에 지오코딩된 단지 좌표 포함(지도 핀) — 좌표 없으면 None(왜곡 없음)."""
    from app.models import Complex
    db.add(Complex(name="레이더단지", lawd_cd="43113", property_type="apartment",
                   lat=36.64, lng=127.42))
    for i, a in enumerate([50000, 51000, 52000, 53000]):
        db.add(_tx("레이더단지", a, f"c{i}", d=date(2026, 2, 1)))
    db.add(_tx("레이더단지", 40000, "low2", d=date(2026, 6, 1), floor=1))
    db.commit()
    r = pc.bargain_radar(db, months=3)
    it = r["items"][0]
    assert it["lat"] == 36.64 and it["lng"] == 127.42
