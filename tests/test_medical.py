"""의료기관 수집 정규화 — WGS84 우선·종별 분류·좌표없음 None·청주 필터(pyproj 불필요한 케이스)."""
from app.sources import medical


def test_medical_wgs84_hospital():
    row = {"기관명": "청주병원", "종별": "종합병원", "소재지도로명주소": "청주시 상당구 용암동",
           "위도": "36.64", "경도": "127.49"}
    o = medical._normalize(row)
    assert o is not None
    assert o["category"] == "living" and o["subcategory"] == "hospital"
    assert o["lawd_cd"] == "43111" and o["course"] == "종합병원"
    assert o["lat"] == 36.64 and o["lng"] == 127.49


def test_medical_pharmacy_subcat():
    row = {"기관명": "청주온누리약국", "종별": "약국", "도로명주소": "청주시 흥덕구 가경동",
           "위도": "36.6", "경도": "127.4"}
    assert medical._normalize(row)["subcategory"] == "pharmacy"


def test_medical_no_coords_is_none():
    # WGS84 없고 TM도 없음 → 좌표 None(틀린 좌표 저장 금지)
    o = medical._normalize({"기관명": "청주의원", "종별": "의원", "도로명주소": "청주시 청원구 율량동"})
    assert o is not None and o["lat"] is None and o["lng"] is None


def test_medical_excludes_non_cheongju():
    assert medical._normalize({"기관명": "서울대병원", "도로명주소": "서울시 종로구"}) is None
