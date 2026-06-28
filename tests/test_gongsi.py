"""공시가격 집계 — 청주만, 단지·면적 중앙값(원→만원), 누락 무시."""
from app.services.gongsi import aggregate_gongsi


def test_aggregate_median_per_complex_cheongju_only():
    rows = [
        {"단지명": "샘플리버뷰", "법정동주소": "충북 청주시 상당구 율량동", "공동주택가격(원)": "300000000", "공시기준일": "2025-01-01"},
        {"단지명": "샘플리버뷰", "법정동주소": "충북 청주시 상당구 율량동", "공동주택가격(원)": "500000000", "공시기준일": "2025-01-01"},
        {"단지명": "딴동네", "법정동주소": "서울特 강남구", "공동주택가격(원)": "900000000"},  # 청주 아님 → 제외
    ]
    out = aggregate_gongsi(rows)
    key = ("샘플리버뷰", "43111")
    assert key in out
    assert out[key]["price_manwon"] == 40000      # median(3억,5억)=4억 → 40000만원
    assert out[key]["basis"] == "2025-01-01"
    assert len(out) == 1                            # 서울 행 제외


def test_missing_price_or_name_ignored():
    rows = [
        {"단지명": "", "법정동주소": "청주시 흥덕구", "공동주택가격(원)": "100000000"},
        {"단지명": "이름만", "법정동주소": "청주시 흥덕구", "공동주택가격(원)": ""},
    ]
    assert aggregate_gongsi(rows) == {}
