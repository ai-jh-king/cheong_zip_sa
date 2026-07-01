"""도서관·어린이집 수집 정규화 — tolerant 필드·청주 필터(네트워크 불필요)."""
from app.sources import library, daycare


def test_library_normalize_cheongju():
    row = {"도서관명": "청주시립도서관", "도서관유형": "공공도서관",
           "소재지도로명주소": "충북 청주시 상당구 ...", "위도": "36.64", "경도": "127.49",
           "열람좌석수": "300"}
    o = library._normalize(row)
    assert o is not None
    assert o["category"] == "living" and o["subcategory"] == "library"
    assert o["lawd_cd"] == "43111" and o["lat"] == 36.64
    assert o["attrs"]["seats"] == 300


def test_library_excludes_non_cheongju():
    assert library._normalize({"도서관명": "서울도서관", "도로명주소": "서울시 중구"}) is None


def test_daycare_normalize_cheongju():
    row = {"어린이집명": "햇살어린이집", "어린이집유형구분": "국공립",
           "주소": "청주시 흥덕구 가경동", "정원": "60", "현원": "55"}
    o = daycare._normalize(row)
    assert o is not None
    assert o["subcategory"] == "daycare" and o["lawd_cd"] == "43113"
    assert o["attrs"]["capacity"] == 60 and o["attrs"]["current"] == 55
    assert o["lat"] is None            # 좌표 없으면 None(거리계산 제외)


def test_daycare_requires_name():
    assert daycare._normalize({"주소": "청주시 상당구"}) is None
