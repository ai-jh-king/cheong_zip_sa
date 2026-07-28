"""정책대출(기금·HF) 요건 매칭 — 백엔드 집중 원칙(프런트는 입력·표시만).

왜곡 없음: 각 요건을 충족(pass)/미충족(fail)/확인 필요(unknown) 3단으로만 평가하고,
전체 결과도 '가능성 있음/요건 미충족'으로만 말한다(승인·한도 판정 금지 — 면책 필수).
"""
from __future__ import annotations

from app.data.finance_rules import POLICY_AS_OF, POLICY_DISCLAIMER, POLICY_PRODUCTS


def _income_cap(p: dict, newlywed: bool, kids2: bool) -> int:
    cap = p["income_max"]
    if newlywed:
        cap = max(cap, p.get("income_max_newlywed", cap))
    if kids2:
        cap = max(cap, p.get("income_max_kids2", cap))
    return cap


def match(purpose: str, income: int | None = None, newlywed: bool = False,
          kids2: bool = False, newborn: bool = False, homeless: bool | None = None,
          amount: int | None = None) -> dict:
    """요건 매칭.

    purpose: buy(구입) | jeonse(전세). income: 부부합산 연소득(만원, None=미입력).
    newlywed: 혼인 7년 이내. kids2: 2자녀 이상. newborn: 2년 내 출산(2023.1.1 이후 출생).
    homeless: 무주택 여부(None=미입력). amount: 주택가 또는 보증금(만원, None=미입력).
    """
    purpose = purpose if purpose in ("buy", "jeonse") else "buy"
    boost = newlywed or kids2
    out = []
    for p in POLICY_PRODUCTS:
        if p["purpose"] not in (purpose, "both"):
            continue
        if p["key"] == "newborn" and not newborn:
            # 신생아 특례는 출산 요건이 핵심 — 미해당이면 목록에서 제외하지 않고 미충족으로 표기
            pass
        checks = []

        def add(label, state, note=None):
            checks.append({"label": label, "state": state, "note": note})

        # 출산 요건(신생아 특례 전용)
        if p["key"] == "newborn":
            add("대출신청일 기준 2년 내 출산(2023.1.1 이후 출생)",
                "pass" if newborn else "fail", None)
        # 소득
        cap = _income_cap(p, newlywed, kids2)
        if income is None:
            add(f"부부합산 연소득 {cap:,}만원 이하", "unknown", "소득 미입력")
        else:
            add(f"부부합산 연소득 {cap:,}만원 이하", "pass" if income <= cap else "fail",
                f"입력 {income:,}만원")
        # 무주택
        if p.get("homeless"):
            if homeless is None:
                add("무주택 세대주", "unknown", "미입력")
            else:
                add("무주택 세대주", "pass" if homeless else "fail", None)
        else:
            add("무주택 또는 처분조건 1주택", "unknown" if homeless is None else ("pass" if homeless else "unknown"),
                "1주택 처분조건은 공고 확인")
        # 가격/보증금 상한
        if purpose == "jeonse" and p.get("price_max_jeonse") is not None:
            pmax = p["price_max_jeonse"]
        else:
            pmax = p.get("price_max_boost") if boost else p["price_max"]
        kind = "주택 가격" if purpose == "buy" else "보증금"
        if amount is None:
            add(f"{kind} {pmax:,}만원 이하", "unknown", "미입력")
        else:
            add(f"{kind} {pmax:,}만원 이하", "pass" if amount <= pmax else "fail",
                f"입력 {amount:,}만원")
        # 한도(정보 표시용 — 판정 아님)
        if purpose == "jeonse" and p.get("limit_jeonse") is not None:
            limit = p["limit_jeonse"]
        else:
            limit = p.get("limit_boost") if boost else p["limit"]

        states = [c["state"] for c in checks]
        overall = "fail" if "fail" in states else ("maybe" if "unknown" in states else "pass")
        out.append({
            "key": p["key"], "name": p["name"], "desc": p["desc"],
            "overall": overall,           # pass=요건 충족 가능성 | maybe=일부 확인 필요 | fail=요건 미충족
            "checks": checks,
            "limit": limit, "extra": p.get("extra"),
            "official_url": p["official_url"],
        })
    # 충족 가능성 높은 순으로 정렬(pass → maybe → fail)
    order = {"pass": 0, "maybe": 1, "fail": 2}
    out.sort(key=lambda x: order[x["overall"]])
    return {"purpose": purpose, "as_of": POLICY_AS_OF, "items": out,
            "disclaimer": POLICY_DISCLAIMER}
