"""
부동산 매수 부대비용 계산 (세금·총비용 계산기).

원칙
  - 법정 요율은 '설정값(COST_RULES)'으로 분리 → 세법/요율 변경 시 값만 수정.
  - 1주택 유상취득(주택) 일반과세 기준. 다주택 중과·조정지역은 별도(현재 청주=비규제, 기본 일반).
  - 국민주택채권·법무사 실비 등 변동 항목은 추정/별도 표기(왜곡 방지: 확정값처럼 단정하지 않음).
  - 결과는 참고용 추정치이며 세무 자문이 아님(화면 고지).

단위: 금액 만원.
"""
from __future__ import annotations

COST_RULES = {
    "as_of": "2025",
    # 중개보수(매매) 상한요율: (상한 매매가 만원, 요율, 한도 만원 or None)
    "broker_brackets": [
        (5000, 0.006, 25),
        (20000, 0.005, 80),
        (90000, 0.004, None),
        (120000, 0.005, None),
        (150000, 0.006, None),
        (float("inf"), 0.007, None),
    ],
    "first_time_acq_credit": 200,   # 생애최초 취득세 감면 한도(만원, 요건 충족 가정)
    "farm_tax_rate": 0.002,         # 농어촌특별세(전용 85㎡ 초과 주택)
    "edu_tax_ratio": 0.10,          # 지방교육세 = 취득세액의 10%
    "beopmu_estimate": 50,          # 법무사 등기대행 예상(만원) — 설정값/추정
}

DISCLAIMER = ("취득세·중개보수 등은 법정 요율 기반 참고용 추정치입니다(1주택 일반과세 기준). "
              "다주택 중과·감면 요건·국민주택채권·법무 실비 등은 사례별로 다르며, 정확한 금액은 "
              "위택스/관할 지자체·법무사·공인중개사에 확인하세요. 본 서비스는 세무자문이 아닙니다.")


def acquisition_rate(price: float) -> float:
    """주택 유상취득 취득세율(1주택 일반). price 만원. 6억 이하 1%, 6~9억 1~3% 선형, 9억 초과 3%."""
    eok = price / 10000  # 만원 → 억
    if eok <= 6:
        return 0.01
    if eok <= 9:
        return round((eok * 2 / 3 - 3) / 100, 6)
    return 0.03


def broker_fee(price: float) -> int:
    for cap, rate, limit in COST_RULES["broker_brackets"]:
        if price < cap:
            fee = price * rate
            if limit is not None:
                fee = min(fee, limit)
            return round(fee)
    return 0


def purchase_costs(price: float, over_85: bool = False,
                   is_first_time: bool = False, is_no_house: bool = True) -> dict:
    acq_rate = acquisition_rate(price)
    acq = price * acq_rate
    credit = 0
    if is_first_time and price <= 120000:  # 생애최초 감면(12억 이하 요건 가정)
        credit = min(acq, COST_RULES["first_time_acq_credit"])
    acq_after = acq - credit
    edu = acq * COST_RULES["edu_tax_ratio"]                       # 지방교육세(표준세율 기준)
    farm = price * COST_RULES["farm_tax_rate"] if over_85 else 0  # 농특세(85㎡ 초과)
    tax_total = acq_after + edu + farm
    broker = broker_fee(price)
    beopmu = COST_RULES["beopmu_estimate"]
    total = round(tax_total + broker + beopmu)
    return {
        "as_of": COST_RULES["as_of"],
        "acq_rate": acq_rate,
        "acquisition_tax": round(acq_after),
        "acquisition_tax_before_credit": round(acq),
        "first_time_credit": round(credit),
        "edu_tax": round(edu),
        "farm_tax": round(farm),
        "over_85": over_85,
        "broker_fee": broker,
        "beopmu_estimate": beopmu,
        "tax_total": round(tax_total),
        "total": total,
        "disclaimer": DISCLAIMER,
    }
