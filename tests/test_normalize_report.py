"""정규화 진단(NormalizationReport) 테스트 — 순수 로직, 외부 의존 없음.

핵심: report 를 넘기지 않으면 normalize_row 동작이 완전히 동일(기존 영향 없음).
"""
from app.sources.molit.normalize import normalize_row, NormalizationReport

GOOD = {"aptNm": "가경아이파크", "umdNm": "가경동", "excluUseAr": "84.97",
        "floor": "10", "dealYear": "2026", "dealMonth": "5", "dealDay": "20",
        "dealAmount": "42,000"}


def test_report_optional_does_not_change_output():
    n = normalize_row(GOOD, property_type="apartment", deal_fetch_type="trade",
                      lawd_cd="43113", source="MOLIT")
    assert n["deal_amount"] == 42000 and n["complex_name"] == "가경아이파크"
    assert "report" not in n  # 반환 형상 불변


def test_good_row_no_miss():
    r = NormalizationReport()
    normalize_row(GOOD, property_type="apartment", deal_fetch_type="trade",
                  lawd_cd="43113", source="MOLIT", report=r)
    assert not r.has_issues()
    assert r.summary()["rows"] == 1


def test_missing_fields_counted():
    r = NormalizationReport()
    bad = {"단지이름": "X", "umdNm": "가경동", "dealYear": "2026",
           "dealMonth": "5", "dealDay": "20"}  # aptNm/excluUseAr/dealAmount 없음
    normalize_row(bad, property_type="apartment", deal_fetch_type="trade",
                  lawd_cd="43113", source="MOLIT", report=r)
    misses = r.summary()["misses"]
    assert misses.get("deal_amount") == 1
    assert misses.get("exclusive_area") == 1
    assert misses.get("complex_name") == 1
    assert r.summary()["miss_samples"]["deal_amount"]  # 원본 키 샘플 보존


def test_rent_does_not_flag_deal_amount():
    r = NormalizationReport()
    rent = {"aptNm": "X", "umdNm": "가경동", "excluUseAr": "59.9",
            "dealYear": "2026", "dealMonth": "5", "dealDay": "1",
            "deposit": "20,000", "monthlyRent": "50"}
    normalize_row(rent, property_type="apartment", deal_fetch_type="rent",
                  lawd_cd="43113", source="MOLIT", report=r)
    assert not r.has_issues()


def test_detached_does_not_flag_name_or_area():
    # 단독·다가구는 단지명/전용면적이 없을 수 있어 핵심 필드에서 제외
    r = NormalizationReport()
    det = {"umdNm": "내수읍", "dealYear": "2026", "dealMonth": "5", "dealDay": "3",
           "dealAmount": "30,000"}
    normalize_row(det, property_type="detached", deal_fetch_type="trade",
                  lawd_cd="43114", source="MOLIT", report=r)
    assert not r.has_issues()
