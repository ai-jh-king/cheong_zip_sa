"""가격 검증 3종 — 판정 없음(사실·백분위·면책)을 검증."""
from datetime import date
from app.models import Transaction
from app.services import pricecheck as pc
from app.core import cache


def _bump():
    cache.bump_data_version()   # 집계 캐시 무효화(테스트 간 오염 방지) — pricecheck 3종은 @stat_cached


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
    db.commit(); _bump()
    r = pc.bargain_radar(db, months=3)
    assert r["items"] and r["items"][0]["name"] == "레이더단지"
    assert r["items"][0]["diff_pct"] <= -12
    assert "단정하지" in r["disclaimer"]


def test_gu_context_medians(db):
    for i, a in enumerate([50000, 60000, 70000]):
        db.add(_tx("맥락단지", a, f"g{i}"))
    db.commit(); _bump()
    r = pc.gu_context(db)
    it = next(x for x in r["items"] if x["lawd_cd"] == "43113")
    assert it["price_median"] == 60000 and it["count"] == 3 and it["ppm_median"] > 0


def _jx(name, dep, key, lawd="43113", d=date(2026, 5, 10)):
    return Transaction(lawd_cd=lawd, property_type="apartment", deal_type="jeonse",
                       complex_name=name, exclusive_area=84.9, contract_date=d,
                       deposit=dep, source="TEST", dedup_key=key)


def test_jeonse_risk_map_flags_high_ratio_with_coords(db):
    """전세가율 높은 단지를 좌표와 함께 나열(지도 핀). 좌표 없으면 제외(왜곡 없음)·판정 없음."""
    from app.models import Complex
    db.add(Complex(name="갭단지", lawd_cd="43113", property_type="apartment", lat=36.64, lng=127.42))
    for i, a in enumerate([50000, 52000, 54000]):
        db.add(_tx("갭단지", a, f"js{i}"))
    for i, dep in enumerate([45000, 46000, 47000]):
        db.add(_jx("갭단지", dep, f"jj{i}"))
    for i, a in enumerate([50000, 52000, 54000]):        # 좌표 없는 단지 → 제외
        db.add(_tx("무좌표단지", a, f"ns{i}"))
    for i, dep in enumerate([45000, 46000, 47000]):
        db.add(_jx("무좌표단지", dep, f"nj{i}"))
    db.commit(); _bump()
    r = pc.jeonse_risk_map(db, min_ratio=75)
    names = [x["name"] for x in r["items"]]
    assert "갭단지" in names
    assert "무좌표단지" not in names
    it = next(x for x in r["items"] if x["name"] == "갭단지")
    assert it["ratio"] == round(46000 / 52000 * 100, 1) and it["lat"] == 36.64
    assert it["level"] in ("elevated", "high")
    assert "단정하지" in r["disclaimer"]


def test_jeonse_risk_map_gates_thin_samples(db):
    """전세 표본이 얇으면(역전세를 단정하지 않기 위해) 핀 제외."""
    from app.models import Complex
    db.add(Complex(name="얇은단지", lawd_cd="43113", property_type="apartment", lat=36.6, lng=127.4))
    for i, a in enumerate([50000, 52000, 54000]):
        db.add(_tx("얇은단지", a, f"ts{i}"))
    db.add(_jx("얇은단지", 46000, "tj0"))       # 전세 1건뿐 → 표본 부족
    db.commit(); _bump()
    r = pc.jeonse_risk_map(db, min_ratio=75)
    assert all(x["name"] != "얇은단지" for x in r["items"])


def test_bargain_radar_includes_coords_when_geocoded(db):
    """급매 항목에 지오코딩된 단지 좌표 포함(지도 핀) — 좌표 없으면 None(왜곡 없음)."""
    from app.models import Complex
    db.add(Complex(name="레이더단지", lawd_cd="43113", property_type="apartment",
                   lat=36.64, lng=127.42))
    for i, a in enumerate([50000, 51000, 52000, 53000]):
        db.add(_tx("레이더단지", a, f"c{i}", d=date(2026, 2, 1)))
    db.add(_tx("레이더단지", 40000, "low2", d=date(2026, 6, 1), floor=1))
    db.commit(); _bump()
    r = pc.bargain_radar(db, months=3)
    it = r["items"][0]
    assert it["lat"] == 36.64 and it["lng"] == 127.42


def test_jeonse_risk_matches_area_band(db):
    """전세가율은 같은 평형 안에서 계산해야 한다 — 큰 평형 매매 vs 작은 평형 전세를 섞으면
    125%·159% 같은 착시가 생김(실사고 v1.257). 평형 매칭 후에는 그런 값이 나오지 않아야."""
    from app.models import Complex
    from app.services import pricecheck
    db.add(Complex(name="평형테스트", lawd_cd="43113", property_type="apartment",
                   dong="가경동", lat=36.63, lng=127.42))
    # 큰 평형(84㎡=25평) 매매 5억대 / 작은 평형(39㎡=12평) 전세 2억대 — 섞으면 40%대로 왜곡되고,
    # 큰 평형 전세 표본이 없으므로 '같은 평형' 규칙에서는 비율을 만들지 않아야 한다.
    for i, a in enumerate([50000, 51000, 52000]):
        db.add(_tx("평형테스트", a, f"big{i}"))                      # 84.9㎡ 매매
    for i, dep in enumerate([20000, 21000, 22000]):
        db.add(Transaction(lawd_cd="43113", property_type="apartment", deal_type="jeonse",
                           complex_name="평형테스트", exclusive_area=39.0,
                           contract_date=date(2026, 5, 1), deposit=dep,
                           source="TEST", dedup_key=f"small{i}"))
    db.commit(); cache.bump_data_version()
    items = pricecheck.jeonse_risk_map(db)["items"]
    assert not [x for x in items if x["name"] == "평형테스트"]   # 평형 불일치 → 신호 없음
