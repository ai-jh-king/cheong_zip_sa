"""단지 보강 — K-apt 기본정보 정규화 매핑(문서 필드 기준)."""
from app.sources.kapt.normalize import normalize_basis


# 문서(공동주택 기본정보 Item)의 실제 필드명 기준 샘플
SAMPLE = {
    "kaptCode": "A13540001", "kaptName": "샘플리버뷰",
    "kaptdaCnt": "1,234", "kaptDongCnt": "12",
    "kaptUsedate": "20190315", "codeHeatNm": "지역난방",
    "kaptTarea": "150000.5", "kaptBcompany": "샘플건설",
}


def test_normalize_basis_maps_documented_fields():
    n = normalize_basis(SAMPLE)
    assert n["kapt_code"] == "A13540001"
    assert n["households"] == 1234        # 콤마 제거 정수화
    assert n["dong_count"] == 12
    assert n["build_year"] == 2019         # 사용승인일 → 연도
    assert n["approval_date"] == "20190315"
    assert n["heating"] == "지역난방"
    assert n["total_area"] == 150000.5
    assert n["builder"] == "샘플건설"
    assert n["meta_source"] == "KAPT"


def test_missing_fields_become_none_not_fabricated():
    n = normalize_basis({"kaptCode": "X", "kaptName": "이름만"})
    assert n["households"] is None        # 날조 금지 → None
    assert n["dong_count"] is None
    assert n["build_year"] is None
    assert n["heating"] is None


def test_empty_item():
    assert normalize_basis({}) == {}


def test_parking_from_ground_plus_basement():
    n = normalize_basis({"kaptCode": "X", "kaptdPcnt": "100", "kaptdPcntu": "250"})
    assert n["parking"] == 350
