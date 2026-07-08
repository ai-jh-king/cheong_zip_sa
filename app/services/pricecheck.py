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
from app.services.stats import PYEONG, _gu_name


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
