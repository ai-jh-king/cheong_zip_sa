"""전세자금대출 계산 — 매매 대출과 구조가 달라 별도(보증금·이자만 납부).

왜곡 없음:
- 한도는 '통상 구조'(보증금 대비 비율)로만 계산하고, 실제 한도는 보증기관·소득·신용으로
  달라진다는 점을 note 로 고지한다. 승인·금리를 보장하지 않는다.
- 정책상품(버팀목·신생아 특례) 해당 여부는 policyloan.match(purpose="jeonse") 재사용 —
  요건표는 finance_rules 한 곳에서만 관리.
- 은행 금리는 실연동(finlife)일 때만 사용하고, 없으면 금리 없이 '한도·구조'만 제공(예시 금리 금지).
"""
from __future__ import annotations

from app.data.finance_rules import RENT_LOAN
from app.services import policyloan

DISCLAIMER = ("전세자금대출 한도·금리는 보증기관(HUG·HF·SGI)과 은행 심사로 확정됩니다. "
              "아래는 공개된 통상 구조와 정책상품 요건에 따른 참고 계산이며 승인을 보장하지 않습니다. "
              "청집사는 어떤 금융회사와도 제휴·수수료 관계가 없습니다.")


def estimate(deposit: float, cash: float | None = None,
             income: int | None = None, homeless: bool | None = None,
             newlywed: bool = False, kids2: bool = False, newborn: bool = False,
             rate_pct: float | None = None) -> dict:
    """전세 보증금 대출 추정.

    deposit: 보증금(만원). cash: 보유현금(만원). rate_pct: 금리(실연동 시에만 전달).
    """
    ltv = RENT_LOAN["ltv_typical"]
    max_by_deposit = round(deposit * ltv)
    need = None if cash is None else max(0, round(deposit - cash))
    # 실제 빌릴 금액 = 필요액과 통상 한도 중 작은 값(현금 미입력이면 통상 한도)
    loan_amount = max_by_deposit if need is None else min(max_by_deposit, need)
    gap = None if need is None else max(0, need - max_by_deposit)   # 한도로도 못 채우는 부족분

    monthly_interest = None
    if rate_pct is not None and loan_amount > 0:
        monthly_interest = round(loan_amount * (rate_pct / 100) / 12)

    policy = policyloan.match("jeonse", income=income, newlywed=newlywed, kids2=kids2,
                              newborn=newborn, homeless=homeless, amount=round(deposit))
    return {
        "deposit": round(deposit),
        "ltv_typical": ltv,
        "max_by_deposit": max_by_deposit,
        "cash": None if cash is None else round(cash),
        "need": need,
        "loan_amount": loan_amount,
        "shortfall": gap,                    # 보증금 - 현금 - 한도 (0 이면 충당 가능)
        "rate_pct": rate_pct,
        "monthly_interest": monthly_interest,  # 전세대출은 통상 이자만 납부
        "repayment": "이자만 납부(만기일시)가 일반적",
        "policy": policy,                     # 버팀목·신생아 특례 요건 매칭(3단 평가)
        "as_of": RENT_LOAN["as_of"],
        "note": RENT_LOAN["note"],
        "disclaimer": DISCLAIMER,
    }
