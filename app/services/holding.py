"""보유 비용 — 재산세(지방세법 계산) + 월 부담 합산.

왜곡 없음:
- 재산세는 **공시가격이 있을 때만** 계산한다(시세로 추정하지 않는다 — 공시가격은 시세와 다름).
  공시가격이 없으면 None 을 돌려주고, UI 는 '공시가격 알리미'에서 확인하도록 안내한다.
- 세부담 상한·감면·다주택 중과는 반영하지 않는다(개별 사안) — note 로 고지.
- 관리비는 공개 데이터가 없어 추정하지 않는다. 사용자가 입력한 값만 합산한다.
"""
from __future__ import annotations

from app.data.finance_rules import PROPERTY_TAX as PT


def _bracket(table: list, base: float) -> float:
    """누진 구간표에서 세액 계산. table=[[상한, 기본세액, 초과세율], ...] (금액 만원)."""
    prev_cap = 0.0
    for cap, fixed, rate in table:
        if base <= cap:
            return fixed + (base - prev_cap) * rate
        prev_cap = cap
    cap, fixed, rate = table[-1]
    return fixed + (base - prev_cap) * rate


def fair_ratio(official_price: float, one_house: bool) -> float:
    """공정시장가액비율 — 1세대 1주택은 공시가 구간별 특례(43~45%), 그 외 60%."""
    if not one_house:
        return PT["fair_ratio_default"]
    for cap, ratio in PT["fair_ratio_one_house"]:
        if official_price <= cap:
            return ratio
    return PT["fair_ratio_one_house"][-1][1]


def property_tax(official_price: float | None, one_house: bool = True,
                 city_area: bool = True) -> dict | None:
    """재산세(연) 추정. official_price=공시가격(만원). None 이면 계산하지 않음(왜곡 방지).

    반환(만원): tax(재산세 본세) · edu(지방교육세) · city(도시지역분) · total(합계) · 근거값.
    """
    if official_price is None or official_price <= 0:
        return None
    ratio = fair_ratio(official_price, one_house)
    base = official_price * ratio                       # 과세표준
    # 1세대 1주택 특례세율은 공시가격 9억 이하만 적용
    use_special = one_house and official_price <= PT["one_house_cap"]
    table = PT["rate_one_house"] if use_special else PT["rate_standard"]
    tax = _bracket(table, base)
    edu = tax * PT["edu_tax_ratio"]
    city = base * PT["city_area_ratio"] if city_area else 0.0
    total = tax + edu + city
    return {
        "official_price": round(official_price),
        "fair_ratio": ratio, "tax_base": round(base),
        "rate_table": "1세대 1주택 특례" if use_special else "표준",
        "tax": round(tax), "edu_tax": round(edu), "city_area_tax": round(city),
        "total": round(total), "monthly": round(total / 12),
        "as_of": PT["as_of"], "source_url": PT["source_url"], "note": PT["note"],
    }


def monthly_burden(loan_monthly: float | None = None,
                   official_price: float | None = None,
                   one_house: bool = True,
                   maintenance_fee: float | None = None,
                   city_area: bool = True) -> dict:
    """매달 실제로 나가는 돈 = 대출 원리금 + 재산세(월분) + 관리비(입력 시).

    각 항목은 '있을 때만' 더한다. 관리비는 공개 데이터가 없어 입력값만 사용(추정 금지).
    """
    tax = property_tax(official_price, one_house=one_house, city_area=city_area)
    parts = []
    total = 0.0
    if loan_monthly:
        parts.append({"key": "loan", "label": "대출 원리금", "amount": round(loan_monthly),
                      "source": "입력 조건 기준 계산"})
        total += loan_monthly
    if tax:
        parts.append({"key": "property_tax", "label": "재산세(월 환산)", "amount": tax["monthly"],
                      "source": f"공시가격 {tax['official_price']:,}만원 · {tax['rate_table']}세율"})
        total += tax["monthly"]
    if maintenance_fee:
        parts.append({"key": "maintenance", "label": "관리비", "amount": round(maintenance_fee),
                      "source": "직접 입력"})
        total += maintenance_fee
    missing = []
    if not official_price:
        missing.append("공시가격(재산세) — 공시가격 알리미에서 확인 후 입력")
    if not maintenance_fee:
        missing.append("관리비 — 단지·평형별로 달라 직접 입력")
    return {"parts": parts, "total": round(total), "property_tax": tax,
            "missing": missing,
            "note": "취득세 등 매수 시 1회성 비용은 제외한 '매달' 부담입니다."}
