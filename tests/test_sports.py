"""체육시설 수집 정규화 — tolerant 필드·청주 필터·사용료(네트워크 불필요)."""
from app.sources import sports


def test_sports_normalize_cheongju():
    row = {"개방시설명": "청주국민체육센터", "개방시설유형구분": "수영장",
           "소재지도로명주소": "충북 청주시 서원구 사직동", "위도": "36.62", "경도": "127.46", "사용료": "3000"}
    o = sports._normalize(row)
    assert o is not None
    assert o["category"] == "sports" and o["subcategory"] == "sports"
    assert o["lawd_cd"] == "43112" and o["course"] == "수영장"
    assert o["tuition"] == 3000 and o["lat"] == 36.62


def test_sports_alt_fields_no_coords():
    row = {"시설명": "흥덕풋살장", "종목명": "풋살", "도로명주소": "청주시 흥덕구 복대동"}
    o = sports._normalize(row)
    assert o is not None
    assert o["lawd_cd"] == "43113" and o["course"] == "풋살" and o["lat"] is None


def test_sports_excludes_non_cheongju():
    assert sports._normalize({"시설명": "서울체육관", "도로명주소": "서울시 송파구"}) is None
