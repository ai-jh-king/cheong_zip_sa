"""학원 수집 정규화(NEIS acaInsTiInfo) — tolerant 필드·세분류·청주 필터(네트워크 불필요).

NEIS는 좌표를 제공하지 않으므로 lat/lng는 None(이후 scripts.geocode로 보강).
NEIS 실제 필드명(ACA_NM 등)과 한글 호환명 모두 흡수하는지 확인.
"""
from app.sources import academy


def test_normalize_neis_fields_lang():
    # NEIS 실제 필드명
    row = {"ACA_NM": "청주영어학원", "REALM_SC_NM": "외국어", "LE_CRSE_NM": "영어회화",
           "FA_RDNMA": "충청북도 청주시 흥덕구 가경동 1", "ADMST_ZONE_NM": "가경동"}
    out = academy._normalize(row)
    assert out is not None
    assert out["name"] == "청주영어학원"
    assert out["subcategory"] == "academy_lang"
    assert out["lawd_cd"] == "43113"               # 흥덕구
    assert out["lat"] is None and out["lng"] is None   # NEIS 좌표 미제공
    assert out["source_dataset"] == "neis_academy"


def test_normalize_korean_fallback_pe():
    # 한글 호환 필드명 + 태권도 → 체육
    row = {"학원명": "상당태권도", "교습과정명": "태권도", "도로명주소": "청주시 상당구 용암동"}
    out = academy._normalize(row)
    assert out is not None
    assert out["subcategory"] == "academy_pe"
    assert out["lawd_cd"] == "43111"


def test_normalize_excludes_non_cheongju():
    row = {"ACA_NM": "서울학원", "FA_RDNMA": "서울특별시 강남구 역삼동"}
    assert academy._normalize(row) is None


def test_normalize_requires_name():
    assert academy._normalize({"REALM_SC_NM": "외국어"}) is None
