"""대출 추천 API (M4). 개인정보 미저장(stateless)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import loan, stats
from app.sources.finlife import fetch_loan_products
from app.sources.hf import fetch_policy_products
from app.sources.seomin import fetch_seomin_products

router = APIRouter(prefix="/loan", tags=["loan"])


class LoanInput(BaseModel):
    price: float = Field(..., description="매매가(만원)")
    consent: bool = False                      # 민감정보 동의 여부
    self_capital: float | None = None          # 보유현금(만원)
    annual_income: float | None = None         # 연소득(만원) — 동의 시에만
    existing_annual_payment: float | None = 0  # 기존 부채 연 상환액(만원)
    is_no_house: bool = True
    is_first_time: bool = False
    over_85: bool = False                      # 전용 85㎡ 초과(농특세)
    rate_pct: float | None = None              # 시뮬 금리(%)
    years: int | None = None                   # 기간(년)


@router.get("/rules")
def rules():
    """현재 적용 중인 규제 파라미터/기본값(공시 시점 포함)."""
    return {**loan.LOAN_RULES, "disclaimer": loan.DISCLAIMER}


class PolicyMatchInput(BaseModel):
    purpose: str = Field("buy", description="buy(구입)/jeonse(전세)")
    income: int | None = Field(None, description="부부합산 연소득(만원)")
    newlywed: bool = False       # 혼인 7년 이내
    kids2: bool = False          # 2자녀 이상
    newborn: bool = False        # 2년 내 출산(2023.1.1 이후 출생)
    homeless: bool | None = None  # 무주택 여부
    amount: int | None = Field(None, description="주택가/보증금(만원)")


@router.post("/policy-match")
def policy_match(body: PolicyMatchInput):
    """정책대출(기금·HF) 요건 매칭 — 가능성 안내(승인·한도 판정 아님, 면책 포함)."""
    from app.services import policyloan
    return policyloan.match(body.purpose, body.income, body.newlywed, body.kids2,
                            body.newborn, body.homeless, body.amount)


@router.get("/protection-rules")
def protection_rules():
    """임차인 보호 규정(청주 적용): 소액임차인 최우선변제 표 + HUG 전세보증 핵심 요건."""
    from app.data import finance_rules as fr
    return {"soak": {"table": fr.SOAK_TABLE_ETC, "note": fr.SOAK_NOTE,
                     "as_of": fr.SOAK_AS_OF, "source_url": fr.SOAK_SOURCE_URL,
                     "region_label": "청주시(그 밖의 지역)"},
            "hug": fr.HUG_RULES,
            "bank_links": [{"name": n, "url": u} for n, u in fr.BANK_LINKS]}


@router.post("/estimate")
def estimate(body: LoanInput):
    # 정책(HF)·은행(finlife 주담대+전세)·서민금융(서민금융 한눈에) — 실연동 있으면 사용, 없으면 예시 폴백.
    live_policy = fetch_policy_products()
    live_bank = fetch_loan_products(limit=10)
    live_seomin = fetch_seomin_products()
    catalog = (live_policy or loan.POLICY_PRODUCTS) + (live_bank or loan.EXAMPLE_BANK)
    if live_seomin:
        catalog = catalog + live_seomin
    rates_live = bool(live_policy or live_bank or live_seomin)
    # 금리 미지정 시: 실연동이면 '시장 대표 금리'를, 아니면 설정 기본값(사용자가 찍는 값 최소화 — v1.253)
    rate = body.rate_pct
    if rate is None and rates_live:
        mk = loan.market_rate(catalog)
        if mk:
            rate = mk["typical"]
    return loan.estimate(
        price=body.price, consent=body.consent, self_capital=body.self_capital,
        annual_income=body.annual_income, existing_annual_payment=body.existing_annual_payment,
        is_no_house=body.is_no_house, is_first_time=body.is_first_time,
        over_85=body.over_85,
        rate_pct=rate, years=body.years,
        products=catalog, rates_live=rates_live,
    )


class RentLoanInput(BaseModel):
    deposit: float = Field(..., description="전세 보증금(만원)")
    cash: float | None = Field(None, description="보유현금(만원)")
    income: int | None = Field(None, description="부부합산 연소득(만원)")
    homeless: bool | None = None
    newlywed: bool = False
    kids2: bool = False
    newborn: bool = False


@router.post("/rent")
def rent_loan(body: RentLoanInput):
    """전세자금대출 — 통상 한도 구조 + 정책상품(버팀목·신생아) 요건 매칭. 금리는 실연동 시에만."""
    from app.services import rentloan
    rate = None
    prods = fetch_loan_products(limit=10) or []
    rents = [p for p in prods if "전세" in str(p.get("name", "")) and p.get("rate_min") is not None]
    if rents:                       # 실연동 전세대출 금리의 대표값(최저~최고 중앙)
        lows = sorted(p["rate_min"] for p in rents)
        highs = sorted(p["rate_max"] for p in rents if p.get("rate_max") is not None) or lows
        rate = round((lows[len(lows) // 2] + highs[len(highs) // 2]) / 2, 2)
    return {**rentloan.estimate(body.deposit, body.cash, body.income, body.homeless,
                                body.newlywed, body.kids2, body.newborn, rate_pct=rate),
            "rates_live": bool(rents)}


class HoldingInput(BaseModel):
    loan_monthly: float | None = Field(None, description="월 원리금(만원)")
    official_price: float | None = Field(None, description="공시가격(만원) — 없으면 재산세 계산 안 함")
    one_house: bool = True
    maintenance_fee: float | None = Field(None, description="월 관리비(만원) — 입력값만 사용")


@router.post("/holding-cost")
def holding_cost(body: HoldingInput):
    """매달 나가는 돈 = 대출 원리금 + 재산세(월) + 관리비. 공시가격 없으면 재산세는 계산하지 않음."""
    from app.services import holding
    return holding.monthly_burden(loan_monthly=body.loan_monthly,
                                  official_price=body.official_price,
                                  one_house=body.one_house,
                                  maintenance_fee=body.maintenance_fee)


class AffordInput(BaseModel):
    self_capital: float = Field(..., description="보유현금(만원)")
    consent: bool = False
    annual_income: float | None = None
    existing_annual_payment: float | None = 0
    is_no_house: bool = True
    is_first_time: bool = False
    over_85: bool = False
    rate_pct: float | None = None
    years: int | None = None
    property_type: str = "apartment"
    lawd_cds: list[str] | None = None
    limit: int = 24


@router.post("/affordable")
def affordable(body: AffordInput, db: Session = Depends(get_db)):
    """보유현금(+소득)으로 살 수 있는 최대 매매가 → 그 예산 이하 단지 매칭.

    각 단지는 중앙값 시세 기준 '자기자본 OO + 대출 OO · 월상환 OO'을 함께 제공.
    금리는 기본 시뮬 금리(공시 변동) 기준 참고치.
    """
    kw = dict(consent=body.consent, annual_income=body.annual_income,
              existing_annual_payment=body.existing_annual_payment,
              is_no_house=body.is_no_house, is_first_time=body.is_first_time,
              over_85=body.over_85, rate_pct=body.rate_pct, years=body.years)
    budget = loan.max_affordable_price(body.self_capital, **kw)
    cxs = stats.affordable_complexes(db, budget, body.property_type, body.limit, body.lawd_cds)

    items = []
    for c in cxs:
        price = c["median_price"]
        e = loan.estimate(price=price, self_capital=body.self_capital, products=loan.PRODUCTS, **kw)
        cost_total = e["costs"]["total"]
        cash_for_house = max(0, body.self_capital - cost_total)   # 부대비용 제외 후 집값에 투입 가능
        loan_needed = min(e["limit"], max(0, round(price - cash_for_house)))
        own = round(price - loan_needed)
        monthly = round(loan.pmt(loan_needed, e["rate_pct"], e["years"])) if loan_needed > 0 else 0
        items.append({**c, "loan_needed": loan_needed, "own_capital": own,
                      "cost_total": cost_total, "monthly_payment": monthly})

    return {
        "budget_max": budget,
        "mode": "personalized" if (body.consent and body.annual_income) else "simple",
        "count": len(items),
        "items": items,
        "rate_pct": (body.rate_pct if body.rate_pct is not None else loan.LOAN_RULES["default_rate"]),
        "years": (body.years if body.years is not None else loan.LOAN_RULES["default_years"]),
        "disclaimer": loan.DISCLAIMER,
    }
