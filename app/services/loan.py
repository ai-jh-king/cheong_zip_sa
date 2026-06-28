"""
대출 추천 계산 (M4 핵심 차별화).

원칙
  - 결과는 공시·정책값 기반 *참고용 추정치*. 금융자문이 아님(화면 고지 필수).
  - 규제 파라미터(LTV/DSR)는 코드 로직에 박지 않고 아래 LOAN_RULES(설정값)로 분리 → 정책 변경 시 값만 수정.
  - 개인정보(소득·부채)는 계산에만 사용하고 저장하지 않음(stateless). 동의 없으면 간이모드(LTV만).
  - 상품표(PRODUCTS)는 finlife/HF 연동 전까지 '예시 공시'이며 is_sample=True 로 표시.

단위: 금액은 모두 '만원'.
"""
from __future__ import annotations

from app.services import costs

# --- 규제 파라미터(정책값·설정) : 청주 = 비규제지역 기준. 변경 시 여기만 수정 -------------
LOAN_RULES = {
    "as_of": "2025-11",                 # 공시/기준 시점(표기용)
    "region": "비규제지역(청주)",
    "ltv": {"기본": 0.70, "생애최초": 0.80},   # 무주택·생애최초 우대
    "dsr": 0.40,                        # 은행권 DSR 한도(연 원리금/연소득)
    "default_rate": 4.0,                # 시뮬 기본 금리(%) — 화면 슬라이더로 조절
    "default_years": 30,
}

# --- 상품표 -----------------------------------------------------------------------------
# 정책대출(디딤돌·보금자리)은 변동이 적어 설정 예시 유지.
# 실연동: app/sources/hf.py (HF 오픈API, data.go.kr 키 재사용). 미연동 시 아래 예시 사용.
# 운영 시에는 HF 공시 금리로 주기적 갱신 권장(공시 기준일 표기).
POLICY_PRODUCTS = [
    {"id": "didimdol", "name": "디딤돌대출", "kind": "정책",
     "rate_min": 2.65, "rate_max": 3.95, "method": "원리금균등",
     "limit": 25000, "req": "무주택·소득요건", "is_sample": True, "as_of": None},
    {"id": "bogeumjari", "name": "보금자리론", "kind": "정책",
     "rate_min": 3.70, "rate_max": 4.00, "method": "원리금균등",
     "limit": 36000, "req": "무주택·주택가격 6억↓", "is_sample": True, "as_of": None},
]
# 은행 상품 — finlife 미연동 시 폴백 예시. 연동되면 실금리로 대체.
EXAMPLE_BANK = [
    {"id": "bank_a", "name": "은행 주택담보대출 A", "kind": "은행",
     "rate_min": 3.90, "rate_max": 5.20, "method": "원리금균등",
     "limit": 50000, "req": "신용·소득 심사", "is_sample": True},
    {"id": "bank_b", "name": "은행 주택담보대출 B", "kind": "은행",
     "rate_min": 4.10, "rate_max": 5.60, "method": "원리금/원금균등",
     "limit": 50000, "req": "신용·소득 심사", "is_sample": True},
]
PRODUCTS = POLICY_PRODUCTS + EXAMPLE_BANK  # 기본(폴백)

DISCLAIMER = ("공시·정책 정보 기반 참고용 추정치입니다. 실제 승인·금리·한도는 개인 신용/소득과 "
              "금융회사 심사로 달라집니다. 본 서비스는 금융자문업이 아니며, 최종 상담은 금융회사·정부 콜센터로 문의하세요.")


def _monthly_rate(rate_pct: float) -> float:
    return rate_pct / 100 / 12


def pmt(principal: float, rate_pct: float, years: int) -> float:
    """원리금균등 월 상환액(만원). principal 만원."""
    i = _monthly_rate(rate_pct)
    n = years * 12
    if principal <= 0:
        return 0.0
    if i == 0:
        return principal / n
    return principal * i / (1 - (1 + i) ** (-n))


def principal_from_payment(monthly_pay: float, rate_pct: float, years: int) -> float:
    """월 상환 가능액 → 원리금균등 기준 대출원금(만원). DSR 한도 역산."""
    i = _monthly_rate(rate_pct)
    n = years * 12
    if monthly_pay <= 0:
        return 0.0
    if i == 0:
        return monthly_pay * n
    return monthly_pay * (1 - (1 + i) ** (-n)) / i


def simulate(principal: float, rate_pct: float, years: int) -> list[dict]:
    """상환방식별 월상환·총이자 시뮬레이션."""
    i = _monthly_rate(rate_pct)
    n = years * 12
    if principal <= 0:
        return []
    # 원리금균등
    m = pmt(principal, rate_pct, years)
    equal_total_int = m * n - principal
    # 원금균등(첫달 최고 → 마지막달 최저), 총이자 = i*P*(n+1)/2
    first = principal / n + principal * i
    last = principal / n + (principal / n) * i
    even_total_int = i * principal * (n + 1) / 2
    # 만기일시(이자만 매월, 원금 만기 일시)
    bullet = principal * i
    return [
        {"method": "원리금균등", "monthly": round(m), "total_interest": round(equal_total_int)},
        {"method": "원금균등", "monthly_first": round(first), "monthly_last": round(last),
         "total_interest": round(even_total_int)},
        {"method": "만기일시", "monthly": round(bullet), "total_interest": round(bullet * n)},
    ]


def max_affordable_price(self_capital: float, *, consent: bool,
                         annual_income: float | None = None,
                         existing_annual_payment: float | None = 0.0,
                         is_no_house: bool = True, is_first_time: bool = False,
                         over_85: bool = False,
                         rate_pct: float | None = None, years: int | None = None) -> int:
    """보유현금으로 살 수 있는 최대 매매가(만원). estimate 의 total_cash_needed(자기자본+부대비용
    기준)가 보유현금을 넘지 않는 최대 가격을 이진탐색 → 대출 탭 숫자와 일관."""
    if not self_capital or self_capital <= 0:
        return 0

    def cash_needed(price: float) -> float:
        if price <= 0:
            return 0.0
        e = estimate(price=price, consent=consent, self_capital=self_capital,
                     annual_income=annual_income, existing_annual_payment=existing_annual_payment,
                     is_no_house=is_no_house, is_first_time=is_first_time, over_85=over_85,
                     rate_pct=rate_pct, years=years, products=PRODUCTS)
        return e["total_cash_needed"]

    lo, hi = 0, 300000  # 상한 30억(만원)
    if cash_needed(hi) <= self_capital:
        return hi
    for _ in range(40):
        mid = (lo + hi) // 2
        if cash_needed(mid) <= self_capital:
            lo = mid
        else:
            hi = mid
        if hi - lo <= 50:
            break
    return int(lo // 100 * 100)  # 100만원 단위로 내림


def _affordability(price, self_capital, annual_income, limit, rate_pct, years, total_cash_gap):
    """실구매력 진단: 부담률(월상환/월소득)·한도 충족·현금 부족으로 적정/빠듯/무리 판정.
    소득·자기자본이 모두 있어야 평가(없으면 None). 저장 안 함(stateless)."""
    if annual_income is None or self_capital is None or annual_income <= 0:
        return None
    required_loan = max(0, round(price - self_capital))
    within_limit = required_loan <= limit
    monthly_income = annual_income / 12.0
    loan_for_calc = required_loan if within_limit else limit   # 한도 초과면 한도까지만 빌린다고 가정
    monthly_pay = pmt(loan_for_calc, rate_pct, years)
    burden = (monthly_pay / monthly_income) if monthly_income else None
    short_cash = bool(total_cash_gap and total_cash_gap > 0)

    if (not within_limit) or short_cash:
        level, label = 4, "무리"
    elif burden is None:
        level, label = 0, "정보부족"
    elif burden <= 0.25:
        level, label = 1, "적정"
    elif burden <= 0.35:
        level, label = 2, "가능하나 빠듯"
    else:
        level, label = 3, "부담 큼"
    return {
        "level": level, "label": label,
        "required_loan": required_loan, "within_limit": within_limit,
        "monthly_payment": round(monthly_pay),
        "burden_ratio": (round(burden * 100, 1) if burden is not None else None),
        "monthly_income": round(monthly_income),
        "cash_gap": total_cash_gap,
        "reason": ("loan_over_limit" if not within_limit else
                   "cash_short" if short_cash else "ok"),
    }


def estimate(*, price: float, consent: bool,
             self_capital: float | None = None,
             annual_income: float | None = None,
             existing_annual_payment: float | None = 0.0,
             is_no_house: bool = True, is_first_time: bool = False,
             over_85: bool = False,
             rate_pct: float | None = None, years: int | None = None,
             products: list[dict] | None = None, rates_live: bool = False) -> dict:
    """대출 한도/상품/월상환 추정. consent=False 또는 소득 미입력 → 간이모드(LTV만).
    products 미지정 시 기본 예시표 사용(POLICY+EXAMPLE_BANK)."""
    rate_pct = rate_pct if rate_pct is not None else LOAN_RULES["default_rate"]
    years = years if years is not None else LOAN_RULES["default_years"]
    catalog = products if products is not None else PRODUCTS

    ltv_ratio = LOAN_RULES["ltv"]["생애최초"] if is_first_time else LOAN_RULES["ltv"]["기본"]
    ltv_amount = round(price * ltv_ratio)

    simple_mode = (not consent) or (annual_income is None)
    dsr_amount = None
    if not simple_mode:
        max_annual = annual_income * LOAN_RULES["dsr"] - (existing_annual_payment or 0)
        dsr_amount = max(0, round(principal_from_payment(max_annual / 12, rate_pct, years)))

    limit = ltv_amount if simple_mode else min(ltv_amount, dsr_amount)
    binding = "LTV" if (simple_mode or limit == ltv_amount) else "DSR"
    needed_cash = max(0, round(price - limit))

    # 매수 부대비용(취득세 등) + 총 필요현금 = 계약금성 자기자본 + 부대비용
    cost = costs.purchase_costs(price, over_85=over_85,
                                is_first_time=is_first_time, is_no_house=is_no_house)
    total_cash_needed = round(needed_cash + cost["total"])
    total_cash_gap = (None if self_capital is None
                      else max(0, round(total_cash_needed - self_capital)))

    # 상품 추천: 정책대출 우선(자격), 금리 오름차순
    prods = []
    for p in catalog:
        ok = True
        if p["kind"] == "정책" and not is_no_house:
            ok = False  # 정책대출 무주택 요건(간단화)
        prods.append({**p, "eligible": ok})
    prods.sort(key=lambda p: (0 if p["kind"] == "정책" and p["eligible"] else 1, p["rate_min"]))

    return {
        "mode": "simple" if simple_mode else "personalized",
        "as_of": LOAN_RULES["as_of"], "region": LOAN_RULES["region"],
        "rate_pct": rate_pct, "years": years,
        "ltv_ratio": ltv_ratio, "ltv_amount": ltv_amount,
        "dsr_ratio": LOAN_RULES["dsr"], "dsr_amount": dsr_amount,
        "limit": limit, "binding": binding,
        "self_capital": self_capital, "needed_cash": needed_cash,
        "cash_gap": (None if self_capital is None else max(0, round(needed_cash - self_capital))),
        "costs": cost,
        "total_cash_needed": total_cash_needed,
        "total_cash_gap": total_cash_gap,
        "affordability": (None if simple_mode else
                          _affordability(price, self_capital, annual_income, limit,
                                         rate_pct, years, total_cash_gap)),
        "simulations": simulate(limit, rate_pct, years),
        "products": prods,
        "rates_live": rates_live,
        "disclaimer": DISCLAIMER,
        "stored": False,  # 개인정보 미저장(stateless)
    }
