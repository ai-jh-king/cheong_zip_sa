"""실거래 신뢰 필터 단위 테스트 — 순수 함수(파싱/판정)만 검증(DB 불필요)."""
from datetime import datetime, date
from types import SimpleNamespace

from app.sources.molit.normalize import _parse_trade_method
from app.services.stats import _reliability, _tx_out


def test_parse_trade_method():
    assert _parse_trade_method({"dealingGbn": "직거래"}) == "direct"
    assert _parse_trade_method({"dealingGbn": "중개거래"}) == "agent"
    assert _parse_trade_method({"거래유형": "직거래"}) == "direct"
    assert _parse_trade_method({"dealingGbn": "-"}) is None
    assert _parse_trade_method({"dealingGbn": ""}) is None
    assert _parse_trade_method({}) is None


def test_reliability_bands():
    assert _reliability(0) == "low"
    assert _reliability(2) == "low"
    assert _reliability(3) == "fair"
    assert _reliability(6) == "fair"
    assert _reliability(7) == "ok"
    assert _reliability(50) == "ok"


def _tx(amount, area, deal_type="trade", corrected=False, method=None):
    return SimpleNamespace(
        deal_type=deal_type, deal_amount=amount, exclusive_area=area, floor=10,
        contract_date=date(2026, 1, 1), deposit=None, monthly_rent=None, is_sample=False,
        corrected_at=(datetime(2026, 1, 2) if corrected else None), trade_method=method,
    )


def test_tx_out_flags():
    # 같은 평형 중앙 평단가(ppm_ref) 대비 ±30% 초과 → outlier
    ref = 1000  # 만원/평
    normal = _tx_out(_tx(34000, 84.9), ppm_ref=ref)   # ppm ≈ 1324 → 32%↑ 이지만 ref=1000 기준이므로 outlier
    assert "outlier" in normal and "corrected" in normal and "direct" in normal

    direct = _tx_out(_tx(20000, 84.9, method="direct"), ppm_ref=ref)
    assert direct["direct"] is True

    corrected = _tx_out(_tx(33000, 84.9, corrected=True), ppm_ref=ref)
    assert corrected["corrected"] is True

    # 전월세는 outlier 판정 대상 아님
    rent = _tx_out(_tx(None, 84.9, deal_type="jeonse"), ppm_ref=ref)
    assert rent["outlier"] is False

    # 기준 평단가 없으면 outlier 판정 보류
    no_ref = _tx_out(_tx(34000, 84.9), ppm_ref=None)
    assert no_ref["outlier"] is False
