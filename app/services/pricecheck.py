"""가격 검증 3종 — '말릴 수 있는 앱'(중개·광고 수익 0) 전략의 창끝.

① quote_check  : 호가 검증 — 입력 가격이 그 단지 최근 실거래에서 어디쯤인지(중앙값 대비 %·백분위).
② gu_context   : 분양가 참고 맥락 — 구별 기존 아파트 평단가·중앙값(분양 탭에 나란히 제공).
③ bargain_radar: 급매 레이더 — 단지 중앙값 대비 크게 낮은 '실거래 사실' 나열.

왜곡 없음 원칙:
- '적정/바가지/급매 확정' 같은 판정 금지. 위치(백분위)·차이(%)·사실만 + 사유 가능성 고지.
- 표본 부족 시 그대로 부족하다고 답함. 모든 응답에 disclaimer.
"""
from __future__ import annotations
from datetime import date, timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Transaction
from app.core.config import get_settings
from app.core.cache import stat_cached
from app.services.stats import PYEONG, _gu_name, rent_gap_signal


def _agg_months() -> int:
    return max(1, getattr(get_settings(), "aggregate_months", 12))

_DISC = "실거래 기반 참고 정보입니다. 층·향·수리상태·특수관계 거래 등으로 개별 가격은 달라질 수 있으며, 적정가를 단정하지 않습니다."


def _recent_trades(db: Session, name: str, lawd: str, pt: str, months: int):
    since = date.today() - timedelta(days=months * 31)
    return list(db.scalars(select(Transaction).where(
        Transaction.deal_type == "trade", Transaction.deal_amount.isnot(None),
        Transaction.is_canceled.isnot(True), Transaction.complex_name == name,
        Transaction.lawd_cd == lawd, Transaction.property_type == pt,
        Transaction.contract_date >= since)))


def quote_check(db: Session, name: str, lawd_cd: str, asking: int,
                property_type: str = "apartment", months: int | None = None) -> dict:
    """① 호가 검증. asking(만원)이 최근 실거래 분포에서 어디인지."""
    months = months or _agg_months()
    rows = _recent_trades(db, name, lawd_cd, property_type, months)
    amts = sorted(r.deal_amount for r in rows)
    if len(amts) < 3:
        return {"found": False, "count": len(amts), "months": months,
                "note": f"최근 {months}개월 실거래가 {len(amts)}건뿐이라 비교가 어려워요(최소 3건 필요).",
                "disclaimer": _DISC}
    med = round(median(amts))
    diff_pct = round((asking - med) / med * 100, 1)
    below = sum(1 for a in amts if a <= asking)
    pctile = round(below / len(amts) * 100)          # 입력가 이하 거래 비율
    return {"found": True, "asking": asking, "median": med, "diff_pct": diff_pct,
            "percentile": pctile, "count": len(amts), "months": months,
            "min": amts[0], "max": amts[-1],
            "note": (f"최근 {months}개월 {len(amts)}건 중앙값 대비 "
                     f"{'+' if diff_pct >= 0 else ''}{diff_pct}% · 이 가격 이하 거래가 {pctile}%입니다."),
            "disclaimer": _DISC}


@stat_cached()
def listing_signal(db: Session, deal_type: str, name: str | None, lawd_cd: str | None,
                   price: int | None, deposit: int | None, area: float | None = None,
                   property_type: str = "apartment") -> dict | None:
    """등록 매물이 그 단지 '실거래 대비' 어디쯤인지 — '말릴 수 있는 앱'의 증명(중개·광고 0이라 매물 위험을 솔직히 표시).
    같은 평형 실거래와 비교(면적 착시 방지). 판정 아님·표본부족/단지 미매칭이면 None(숨김).
    - 매매: 중앙값 대비 %·백분위 + 급매(≤-12%) 사실 표시.
    - 전세: 보증금÷단지 매매 중앙값 = 이 매물의 전세가율 → 역전세 유의 신호(단정 아님)."""
    if not (name and lawd_cd):
        return None
    months = _agg_months()
    rows = _recent_trades(db, name, lawd_cd, property_type, months)
    if area:                                   # 같은 평형만(면적 착시 방지)
        py = round(area / PYEONG)
        rows = [r for r in rows if r.exclusive_area and round(r.exclusive_area / PYEONG) == py]
    amts = sorted(r.deal_amount for r in rows)
    if len(amts) < 3:                          # 표본 부족 → 비교 안 함(왜곡 방지)
        return None
    med = round(median(amts))
    if deal_type == "trade" and price:
        diff = round((price - med) / med * 100, 1)
        below = sum(1 for a in amts if a <= price)
        return {"kind": "trade", "median": med, "diff_pct": diff,
                "percentile": round(below / len(amts) * 100), "count": len(amts),
                "months": months, "bargain": diff <= -12, "disclaimer": _DISC}
    if deal_type == "jeonse" and deposit:
        ratio = round(deposit / med * 100, 1)
        sig = rent_gap_signal(ratio)
        return {"kind": "jeonse", "jeonse_ratio": ratio, "sale_median": med,
                "count": len(amts), "level": sig["level"] if sig else None,
                "note": sig["note"] if sig else None,
                "disclaimer": "이 보증금을 같은 평형 매매 중앙값과 비교한 전세가율입니다. "
                              "개별 계약·선순위 채권·시점에 따라 다르며 역전세를 단정하지 않습니다."}
    return None


def gu_context(db: Session, months: int | None = None) -> dict:
    """② 구별 기존 아파트 시세 맥락(분양가 옆에 참고로). 평단가·중앙값·표본수."""
    months = months or _agg_months()
    since = date.today() - timedelta(days=months * 31)
    rows = db.execute(select(Transaction.lawd_cd, Transaction.deal_amount,
                             Transaction.exclusive_area).where(
        Transaction.deal_type == "trade", Transaction.deal_amount.isnot(None),
        Transaction.exclusive_area.isnot(None), Transaction.is_canceled.isnot(True),
        Transaction.property_type == "apartment",
        Transaction.contract_date >= since)).all()
    by: dict = {}
    for lawd, amt, area in rows:
        by.setdefault(lawd, []).append((amt, amt / (area / PYEONG)))
    out = []
    for lawd, v in sorted(by.items()):
        out.append({"lawd_cd": lawd, "gu": _gu_name(lawd), "count": len(v),
                    "price_median": round(median([x[0] for x in v])),
                    "ppm_median": round(median([x[1] for x in v]))})
    return {"months": months, "items": out,
            "disclaimer": "기존 아파트 실거래 기준 참고 맥락입니다. 분양가와의 비교 판단(입지·신축 프리미엄 등)은 여러 요인을 함께 보세요."}


@stat_cached()
def bargain_radar(db: Session, months: int = 3, threshold_pct: float = -12.0,
                  limit: int = 12) -> dict:
    """③ 급매 레이더: 최근 실거래 중 '그 단지 최근 12개월 중앙값' 대비 threshold 이하 사례.
    '급매 확정'이 아니라 낮은 가격 거래 '사실'의 나열(사유 가능성 고지)."""
    since = date.today() - timedelta(days=months * 31)
    recent = list(db.scalars(select(Transaction).where(
        Transaction.deal_type == "trade", Transaction.deal_amount.isnot(None),
        Transaction.is_canceled.isnot(True), Transaction.property_type == "apartment",
        Transaction.contract_date >= since)))
    # 단지×평형 중앙값(12개월) — 같은 평형끼리 비교(면적 차이로 인한 착시 방지)
    base_since = date.today() - timedelta(days=12 * 31)
    base_rows = db.execute(select(Transaction.complex_name, Transaction.lawd_cd,
                                  Transaction.exclusive_area, Transaction.deal_amount).where(
        Transaction.deal_type == "trade", Transaction.deal_amount.isnot(None),
        Transaction.is_canceled.isnot(True), Transaction.property_type == "apartment",
        Transaction.contract_date >= base_since, Transaction.exclusive_area.isnot(None))).all()
    base: dict = {}
    for nm, lawd, area, amt in base_rows:
        base.setdefault((nm, lawd, round(area / PYEONG)), []).append(amt)
    hits = []
    for r in recent:
        if not r.exclusive_area:
            continue
        key = (r.complex_name, r.lawd_cd, round(r.exclusive_area / PYEONG))
        amts = base.get(key) or []
        if len(amts) < 4:                      # 소표본 착시 방지
            continue
        med = median(amts)
        diff = round((r.deal_amount - med) / med * 100, 1)
        if diff <= threshold_pct:
            hits.append({"name": r.complex_name, "gu": _gu_name(r.lawd_cd),
                         "lawd_cd": r.lawd_cd, "pyeong": key[2], "floor": r.floor,
                         "date": r.contract_date.isoformat() if r.contract_date else None,
                         "amount": r.deal_amount, "median": round(med), "diff_pct": diff})
    hits.sort(key=lambda x: x["diff_pct"])
    hits = hits[:limit]
    # 지도 핀용 좌표(지오코딩된 단지만, 없으면 None → 프런트 핀 제외. 왜곡 없음)
    if hits:
        from app.models import Complex
        keys = {(h["name"], h["lawd_cd"]) for h in hits}
        coord = {}
        for cx in db.scalars(select(Complex).where(
                Complex.name.in_({k[0] for k in keys}),
                Complex.lawd_cd.in_({k[1] for k in keys}),
                Complex.lat.isnot(None))):
            coord[(cx.name, cx.lawd_cd)] = (cx.lat, cx.lng)
        for h in hits:
            ll = coord.get((h["name"], h["lawd_cd"]))
            h["lat"], h["lng"] = (ll if ll else (None, None))
    return {"months": months, "threshold_pct": threshold_pct, "items": hits,
            "disclaimer": ("같은 평형의 12개월 중앙값 대비 낮게 신고된 실거래 '사실'입니다. "
                           "저층·수리필요·가족 간 거래 등 사유가 있을 수 있어 '급매'를 단정하지 않습니다.")}


@stat_cached()
def jeonse_risk_map(db: Session, months: int | None = None, min_ratio: float = 75.0,
                    min_sample: int = 3, limit: int = 200) -> dict:
    """전세가율(전세보증금 중앙값 ÷ 매매가 중앙값)이 높은 단지를 '사실'로 나열 — '판단이 얹힌 지도'용.
    청주 최대 화두(갭투자·역전세)의 공간 신호. 역전세 '단정' 금지, 표본 게이팅, 좌표 없으면 제외(왜곡 없음).
    단지 상세의 jeonse_ratio(median 전세보증금/median 매매가)와 동일한 산식."""
    months = months or _agg_months()
    since = date.today() - timedelta(days=months * 31)
    rows = db.execute(select(Transaction.complex_name, Transaction.lawd_cd,
                             Transaction.deal_type, Transaction.deal_amount,
                             Transaction.deposit).where(
        Transaction.property_type == "apartment", Transaction.is_canceled.isnot(True),
        Transaction.complex_name.isnot(None), Transaction.contract_date >= since)).all()
    agg: dict = {}
    for nm, lawd, dt, amt, dep in rows:
        if not nm:
            continue
        g = agg.setdefault((nm, lawd), {"sale": [], "jeonse": []})
        if dt == "trade" and amt:
            g["sale"].append(amt)
        elif dt == "jeonse" and dep:
            g["jeonse"].append(dep)
    # 지오코딩된 단지만 좌표 부여 → 없으면 핀 제외(왜곡 없음)
    from app.models import Complex
    coord = {(cx.name, cx.lawd_cd): (cx.lat, cx.lng)
             for cx in db.scalars(select(Complex).where(Complex.lat.isnot(None)))}
    items = []
    for (nm, lawd), g in agg.items():
        # 매매·전세 둘 다 표본이 충분할 때만(얇은 표본으로 역전세 위험을 단정하지 않기 위해)
        if len(g["sale"]) < min_sample or len(g["jeonse"]) < min_sample:
            continue
        ll = coord.get((nm, lawd))
        if not ll or ll[0] is None:
            continue
        sale_med = median(g["sale"])
        if not sale_med:
            continue
        ratio = round(median(g["jeonse"]) / sale_med * 100, 1)
        if ratio < min_ratio:
            continue
        items.append({"name": nm, "gu": _gu_name(lawd), "lawd_cd": lawd,
                      "lat": ll[0], "lng": ll[1], "ratio": ratio,
                      "level": "high" if ratio >= 85 else "elevated",
                      "sale_count": len(g["sale"]), "jeonse_count": len(g["jeonse"])})
    items.sort(key=lambda x: -x["ratio"])
    items = items[:limit]
    return {"months": months, "min_ratio": min_ratio, "items": items,
            "disclaimer": ("전세보증금 중앙값 ÷ 매매가 중앙값(최근 실거래)이 높은 단지 '사실'입니다. "
                           "전세가율이 높을수록 시세 하락 시 보증금 회수가 어려워질 수 있으나, 실제 위험은 "
                           "등기부·선순위 채권·개별 계약으로 달라지며 역전세를 단정하지 않습니다.")}
