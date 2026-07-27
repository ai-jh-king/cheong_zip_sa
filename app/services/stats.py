"""
집계 서비스 (M2). Transaction(캐싱된 실거래) → 대시보드 수치.

왜곡 없음 원칙:
  - 표본이 없거나 부족하면 평균/등락폭을 '지어내지 않고' None + 사유 플래그를 반환.
  - 전월/전년 대비는 양쪽 달 데이터가 모두 있을 때만 계산.
  - 전세가율은 같은 지역·유형의 평균 전세보증금 / 평균 매매가(근사)이며 근사임을 명시.
  - 집계는 캐싱 데이터 위에서 Python 으로 수행(DB 방언 비의존). 대규모화 시 SQL 집계로 이전.
"""
from __future__ import annotations
from datetime import date
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.region_codes import CHEONGJU_DISTRICTS, DISTRICT_CENTROIDS
from app.models import Transaction
from app.core.cache import stat_cached
from app.core.config import get_settings

LOW_SAMPLE_THRESHOLD = 5


def _avg(vals) -> int | None:
    vals = [v for v in vals if v is not None]
    return round(mean(vals)) if vals else None


def _month_key(d: date | None) -> str | None:
    return f"{d.year}-{d.month:02d}" if d else None


def _pct_change(curr: int | None, prev: int | None) -> float | None:
    if curr is None or prev in (None, 0):
        return None
    return round((curr - prev) / prev * 100, 1)


def _cutoff_date(months: int | None = None) -> date:
    """집계 윈도우 시작일(최근 N개월의 1일). 기본 N = settings.aggregate_months(12)."""
    n = months if months is not None else get_settings().aggregate_months
    t = date.today()
    y, m = t.year, t.month - n
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


# 집계에서 실제 사용하는 컬럼만(메모리 절약). 전체 ORM 엔티티 대신 경량 Row를 조회한다.
# ⚠️ stats.py 어디서든 _load* 결과 행에 새 컬럼을 접근하게 되면 반드시 여기에 추가할 것
#    (누락 시 AttributeError). 현재 소비 컬럼 전수 조사 기준.
_AGG_COLS = (
    Transaction.deal_type, Transaction.deal_amount, Transaction.deposit,
    Transaction.monthly_rent, Transaction.contract_date, Transaction.exclusive_area,
    Transaction.floor, Transaction.complex_name, Transaction.dong_name,
    Transaction.lawd_cd, Transaction.property_type, Transaction.build_year,
    Transaction.trade_method, Transaction.is_sample, Transaction.is_canceled,
    Transaction.corrected_at,
)


def _load_window(db: Session, property_type: str, months: int | None) -> list:
    """집계 로더 — 최근 N개월만 **SQL에서** 필터 + **필요한 컬럼만** 조회(메모리 보호).
    전체 ORM 객체 대신 경량 Row 반환 → 행당 메모리 대폭 절감 + identity map 미사용(대량 집계 OOM 방지).
    months=None이면 전체. 해제분 제외 + 유형 필터. 반환 행은 r.deal_amount 처럼 컬럼명 속성으로 접근
    (소비 코드 변경 불필요)."""
    stmt = select(*_AGG_COLS).where(Transaction.is_canceled.isnot(True))  # 해제분 제외
    if property_type and property_type != "all":
        stmt = stmt.where(Transaction.property_type == property_type)
    if months is not None:
        stmt = stmt.where(Transaction.contract_date >= _cutoff_date(months))
    return db.execute(stmt).all()


def _rows_where(db: Session, *conds) -> list:
    """집계용 경량 행 조회(조건 직접 지정). _load_window 와 동일하게 _AGG_COLS 만 가져온다."""
    return db.execute(select(*_AGG_COLS).where(*conds)).all()


def _load_all(db: Session, property_type: str) -> list[Transaction]:
    """전체 이력(특수 용도). 일반 집계는 _load/_load_window 를 쓸 것(메모리 보호)."""
    return _load_window(db, property_type, None)


def _load(db: Session, property_type: str) -> list[Transaction]:
    """집계 기본 로더 — 최근 aggregate_months(기본 12개월)만, SQL에서 윈도우 필터.
    '현재 시세'(중앙값·평단가·전세가율·거래량·랭킹 등)는 이 윈도우 기준."""
    return _load_window(db, property_type, get_settings().aggregate_months)


def _monthly_trade_avgs(rows: list[Transaction]) -> dict[str, int]:
    """계약월 → 매매 평균. (해당 월 거래 있는 경우만)"""
    buckets: dict[str, list[int]] = {}
    for r in rows:
        if r.deal_type == "trade" and r.deal_amount and r.contract_date:
            buckets.setdefault(_month_key(r.contract_date), []).append(r.deal_amount)
    return {k: round(mean(v)) for k, v in buckets.items()}


def _delta_month_year(monthly: dict[str, int]) -> tuple[float | None, float | None, str | None]:
    """최신월 기준 전월·전년 대비. 데이터 없으면 None."""
    if not monthly:
        return None, None, None
    latest = max(monthly.keys())
    y, m = map(int, latest.split("-"))
    prev_m = f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"
    prev_y = f"{y - 1}-{m:02d}"
    dM = _pct_change(monthly[latest], monthly.get(prev_m))
    dY = _pct_change(monthly[latest], monthly.get(prev_y))
    return dM, dY, latest


@stat_cached()
def city_summary(db: Session, property_type: str = "apartment") -> dict:
    rows = _load(db, property_type)               # 최근 N개월(헤드라인 평균)
    trade = [r.deal_amount for r in rows if r.deal_type == "trade" and r.deal_amount]
    jeon = [r.deposit for r in rows if r.deal_type == "jeonse" and r.deposit]
    wol = [r.monthly_rent for r in rows if r.deal_type == "wolse" and r.monthly_rent]
    wol_dep = [r.deposit for r in rows if r.deal_type == "wolse" and r.deposit]

    monthly = _monthly_trade_avgs(_load_window(db, property_type, 16))  # 전월/전년 대비: 최근 16개월(YoY+지연 버퍼)
    dM, dY, latest = _delta_month_year(monthly)

    return {
        "as_of": latest,
        "avg_mae": _avg(trade), "avg_jeon": _avg(jeon),
        "avg_wol": _avg(wol), "avg_wol_deposit": _avg(wol_dep),
        "mae_dM": dM, "mae_dY": dY,
        "insufficient": {"dM": dM is None, "dY": dY is None},
        "trade_count": len(trade),
    }


@stat_cached()
def by_region(db: Session, property_type: str = "apartment") -> list[dict]:
    out = []
    for d in CHEONGJU_DISTRICTS:
        rows = _rows_where(
            db,
            Transaction.property_type == property_type,
            Transaction.lawd_cd == d.code,
            Transaction.contract_date >= _cutoff_date(16),  # 최근 16개월(메모리·현재시세)
            Transaction.is_canceled.isnot(True),  # 해제분 제외
        )
        trade = [r.deal_amount for r in rows if r.deal_type == "trade" and r.deal_amount]
        jeon = [r.deposit for r in rows if r.deal_type == "jeonse" and r.deposit]
        monthly = _monthly_trade_avgs(rows)
        dM, _, _ = _delta_month_year(monthly)
        avg_mae, avg_jeon = _avg(trade), _avg(jeon)
        jeon_rate = round(avg_jeon / avg_mae * 100, 1) if (avg_mae and avg_jeon) else None
        out.append({
            "code": d.code, "name": f"청주시 {d.name}",
            "avg_mae": avg_mae, "trade_count": len(trade),
            "mae_dM": dM, "jeon_rate": jeon_rate,
            "low_sample": len(trade) < LOW_SAMPLE_THRESHOLD,
        })
    return out


@stat_cached()
def trend(db: Session, property_type: str = "apartment", months: int = 6) -> dict:
    """최근 N개월 구별 매매 평균 시계열. 데이터 없는 칸은 None(미보간)."""
    today = date.today().replace(day=1)
    keys: list[str] = []
    y, m = today.year, today.month
    for _ in range(months):
        keys.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys = list(reversed(keys))

    series = []
    contains_sample = False
    for d in CHEONGJU_DISTRICTS:
        rows = _rows_where(
            db,
            Transaction.property_type == property_type,
            Transaction.lawd_cd == d.code,
            Transaction.contract_date >= _cutoff_date(months + 2),  # 표시 구간 + 버퍼만
            Transaction.is_canceled.isnot(True),  # 해제분 제외
        )
        contains_sample = contains_sample or any(r.is_sample for r in rows)
        monthly = _monthly_trade_avgs(rows)
        series.append({
            "code": d.code, "name": f"청주시 {d.name}",
            "values": [monthly.get(k) for k in keys],
        })
    return {"months": keys, "series": series, "contains_sample_data": contains_sample}


# ============================================================================
#  랭킹 (첫 화면 매매 순위 / 하단 고정: 활발 구 · 등락 큰 집)
# ============================================================================
from app.data.region_codes import DISTRICT_BY_CODE


def _gu_name(code: str) -> str:
    d = DISTRICT_BY_CODE.get(code)
    return f"청주시 {d.name}" if d else code


def _band_rows(rows, area_band):
    if not area_band or area_band == "all":
        return rows
    return [r for r in rows if _bucket(r.exclusive_area) == area_band]


@stat_cached()
def top_trades(db: Session, property_type: str = "apartment", limit: int = 15,
               area_band: str = "all") -> list[dict]:
    """청주시 전체 매매가 순위(내림차순). 개별 실거래 기준."""
    rows = [r for r in _load(db, property_type)
            if r.deal_type == "trade" and r.deal_amount]
    rows = _band_rows(rows, area_band)
    rows.sort(key=lambda r: r.deal_amount, reverse=True)
    out = []
    for i, r in enumerate(rows[:limit], 1):
        out.append({
            "rank": i,
            "complex_name": r.complex_name,
            "gu": _gu_name(r.lawd_cd), "lawd_cd": r.lawd_cd, "dong": r.dong_name,
            "property_type": r.property_type,
            "exclusive_area": r.exclusive_area, "floor": r.floor,
            "contract_date": r.contract_date.isoformat() if r.contract_date else None,
            "deal_amount": r.deal_amount,
            "price_per_m2": round(r.deal_amount / r.exclusive_area, 1)
            if r.exclusive_area else None,
            "is_sample": r.is_sample,
        })
    return out


@stat_cached()
def active_regions(db: Session, property_type: str = "all") -> list[dict]:
    """지금 가장 활발히 거래되는 구 순위 = 최근월 거래건수(동률 시 전체건수)."""
    rows = [r for r in _load(db, property_type)
            if r.deal_type == "trade" and r.contract_date]
    if not rows:
        return [{"rank": i + 1, "code": d.code, "name": _gu_name(d.code),
                 "recent_count": 0, "total_count": 0, "recent_month": None}
                for i, d in enumerate(CHEONGJU_DISTRICTS)]
    latest = max(_month_key(r.contract_date) for r in rows)
    agg: dict[str, dict] = {}
    for r in rows:
        a = agg.setdefault(r.lawd_cd, {"recent": 0, "total": 0})
        a["total"] += 1
        if _month_key(r.contract_date) == latest:
            a["recent"] += 1
    items = []
    for d in CHEONGJU_DISTRICTS:
        a = agg.get(d.code, {"recent": 0, "total": 0})
        items.append({"code": d.code, "name": _gu_name(d.code),
                      "recent_count": a["recent"], "total_count": a["total"],
                      "recent_month": latest})
    items.sort(key=lambda x: (x["recent_count"], x["total_count"]), reverse=True)
    for i, it in enumerate(items, 1):
        it["rank"] = i
    return items


@stat_cached()
def complex_movers(db: Session, property_type: str = "apartment", limit: int = 8) -> list[dict]:
    """최근 등락폭이 큰 집(단지) 순위. 단지별 최근월 평균 vs 직전월 평균 % 변화.
    데이터(2개월 이상) 없는 단지는 제외 — 등락을 지어내지 않는다."""
    by_cx: dict[str, dict] = {}
    for r in _load(db, property_type):
        if r.deal_type != "trade" or not r.deal_amount or not r.contract_date or not r.complex_name:
            continue
        c = by_cx.setdefault(r.complex_name, {"gu": r.lawd_cd, "months": {},
                                              "is_sample": False})
        c["months"].setdefault(_month_key(r.contract_date), []).append(r.deal_amount)
        c["is_sample"] = c["is_sample"] or r.is_sample

    movers = []
    for name, c in by_cx.items():
        if len(c["months"]) < 2:
            continue
        keys = sorted(c["months"].keys())
        latest, prev = keys[-1], keys[-2]
        cur_avg = round(mean(c["months"][latest]))
        prev_avg = round(mean(c["months"][prev]))
        chg = _pct_change(cur_avg, prev_avg)
        if chg is None:
            continue
        movers.append({
            "complex_name": name, "gu": _gu_name(c["gu"]),
            "latest_amount": cur_avg, "prev_amount": prev_avg,
            "change_pct": chg, "direction": "up" if chg >= 0 else "down",
            "latest_month": latest, "prev_month": prev,
            "is_sample": c["is_sample"],
        })
    movers.sort(key=lambda m: abs(m["change_pct"]), reverse=True)
    for i, m in enumerate(movers[:limit], 1):
        m["rank"] = i
    return movers[:limit]


# ============================================================================
#  홈 화면용 지표: 평형대별 평단가(중앙값) · 거래량 · 신고가
#  (시 전체 평균의 한계를 보완 — 평단가/중앙값/면적대로 분리)
# ============================================================================
from statistics import median

PYEONG = 3.305785  # 1평 = 3.305785㎡
AREA_BUCKETS = [
    ("small", "소형 (~60㎡)", 0, 60),
    ("medium", "중형 (60~85㎡)", 60, 85),
    ("large", "대형 (85㎡~)", 85, 10**9),
]


def _bucket(area):
    if area is None:
        return None
    for key, _l, lo, hi in AREA_BUCKETS:
        if lo <= area < hi:
            return key
    return None


def _pyeong_unit(amount: int, area_m2: float) -> float:
    """만원/평 = 거래금액 ÷ (전용면적/3.305785)"""
    return amount / (area_m2 / PYEONG)


@stat_cached()
def ppm_by_area(db: Session, property_type: str = "apartment") -> dict:
    """면적대별 평단가(만원/평) 중앙값 + 표본수. 평균 대신 median 사용(이상치 견고)."""
    rows = [r for r in _load(db, property_type)
            if r.deal_type == "trade" and r.deal_amount and r.exclusive_area]
    buckets = []
    for key, label, lo, hi in AREA_BUCKETS:
        vals = [_pyeong_unit(r.deal_amount, r.exclusive_area)
                for r in rows if lo <= r.exclusive_area < hi]
        buckets.append({"bucket": key, "label": label,
                        "median_pyeong": round(median(vals)) if vals else None,
                        "count": len(vals)})
    allv = [_pyeong_unit(r.deal_amount, r.exclusive_area) for r in rows]
    return {"buckets": buckets,
            "total_median_pyeong": round(median(allv)) if allv else None,
            "total_count": len(allv)}


@stat_cached()
def volume(db: Session, property_type: str = "apartment") -> dict:
    """최근월 매매 거래량 + 전월 대비(건수 기준)."""
    monthly: dict[str, int] = {}
    for r in _load(db, property_type):
        if r.deal_type == "trade" and r.contract_date:
            monthly[_month_key(r.contract_date)] = monthly.get(_month_key(r.contract_date), 0) + 1
    if not monthly:
        return {"month": None, "count": 0, "prev_count": None, "dM": None}
    latest = max(monthly)
    y, m = map(int, latest.split("-"))
    prev = f"{y-1}-12" if m == 1 else f"{y}-{m-1:02d}"
    cur, pv = monthly[latest], monthly.get(prev)
    dM = round((cur - pv) / pv * 100, 1) if pv else None
    return {"month": latest, "count": cur, "prev_count": pv, "dM": dM}


@stat_cached()
def newly_high(db: Session, property_type: str = "apartment", limit: int = 8) -> list[dict]:
    """신고가: 단지×면적대 그룹에서 최근월 최고가가 '이전 모든 달의 최고가'를 넘은 경우.
    이전 기록이 없으면(거래 1개월뿐) 제외 — 신고가를 지어내지 않는다."""
    groups: dict[tuple, dict] = {}
    for r in _load(db, property_type):
        if r.deal_type != "trade" or not r.deal_amount or not r.contract_date or not r.complex_name:
            continue
        b = _bucket(r.exclusive_area)
        g = groups.setdefault((r.complex_name, b),
                              {"gu": r.lawd_cd, "months": {}, "is_sample": False, "bucket": b})
        g["months"].setdefault(_month_key(r.contract_date), []).append(r.deal_amount)
        g["is_sample"] = g["is_sample"] or r.is_sample

    blabel = {k: l for k, l, _lo, _hi in AREA_BUCKETS}
    out = []
    for (name, b), g in groups.items():
        keys = sorted(g["months"])
        if len(keys) < 2:
            continue
        latest = keys[-1]
        latest_max = max(g["months"][latest])
        prev_high = max(v for k in keys[:-1] for v in g["months"][k])
        if latest_max > prev_high:
            out.append({
                "complex_name": name, "gu": _gu_name(g["gu"]),
                "area_label": blabel.get(b, "-"),
                "latest_amount": latest_max, "prev_high": prev_high,
                "change_pct": round((latest_max - prev_high) / prev_high * 100, 1),
                "month": latest, "is_sample": g["is_sample"],
            })
    out.sort(key=lambda x: x["change_pct"], reverse=True)
    return out[:limit]


@stat_cached()
def top_trades_by_ppm(db: Session, property_type: str = "apartment", limit: int = 15,
                      area_band: str = "all") -> list[dict]:
    """평단가(만원/평) 순위 — 절대가격이 아닌 단가 기준 공정 비교."""
    rows = [r for r in _load(db, property_type)
            if r.deal_type == "trade" and r.deal_amount and r.exclusive_area]
    rows = _band_rows(rows, area_band)
    scored = [(round(_pyeong_unit(r.deal_amount, r.exclusive_area)), r) for r in rows]
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for i, (pp, r) in enumerate(scored[:limit], 1):
        out.append({
            "rank": i, "complex_name": r.complex_name, "gu": _gu_name(r.lawd_cd),
            "lawd_cd": r.lawd_cd, "dong": r.dong_name, "property_type": r.property_type,
            "exclusive_area": r.exclusive_area, "floor": r.floor,
            "contract_date": r.contract_date.isoformat() if r.contract_date else None,
            "deal_amount": r.deal_amount, "pyeong_unit": pp, "is_sample": r.is_sample,
        })
    return out


# ============================================================================
#  단지 상세 (M3) — 보유 실거래로 시세추이·전고점대비·면적별 평단가·거래량
# ============================================================================
from app.models import Complex


def _ppm_of(r):
    return _pyeong_unit(r.deal_amount, r.exclusive_area) if (r.deal_amount and r.exclusive_area) else None


def _reliability(n: int) -> str:
    """표본 신뢰도: 거래건수 기반. low(매우 적음)/fair(적음)/ok."""
    return "low" if n < 3 else ("fair" if n < 7 else "ok")


def _tx_out(r, ppm_ref=None) -> dict:
    """최근 실거래 1행 출력 + 신뢰 플래그(정정/직거래/이상치).
    outlier: 매매이면서 같은 평형 중앙 평단가 대비 ±30% 초과 이탈.
    """
    pm = _ppm_of(r) if r.deal_type == "trade" else None
    outlier = bool(r.deal_type == "trade" and ppm_ref and pm and abs(pm - ppm_ref) / ppm_ref > 0.30)
    return {
        "deal_type": r.deal_type, "exclusive_area": r.exclusive_area, "floor": r.floor,
        "contract_date": r.contract_date.isoformat() if r.contract_date else None,
        "deal_amount": r.deal_amount, "deposit": r.deposit, "monthly_rent": r.monthly_rent,
        "is_sample": r.is_sample,
        "corrected": r.corrected_at is not None,
        "direct": (r.trade_method == "direct"),
        "outlier": outlier,
    }


def _area_block(area: float, rows_area: list) -> dict:
    """(아파트×면적) 한 면적의 상세: 최근가·중앙값·전저점/전고점·전세가율·추이·최근거래."""
    trades = [r for r in rows_area if r.deal_type == "trade" and r.deal_amount]
    amts = sorted(r.deal_amount for r in trades)
    median_p = round(median(amts)) if amts else None
    peak = amts[-1] if amts else None
    trough = amts[0] if amts else None
    latest_tx = max(trades, key=lambda r: (r.contract_date or date.min)) if trades else None
    latest = latest_tx.deal_amount if latest_tx else None
    from_peak = round((latest - peak) / peak * 100, 1) if (peak and latest) else None
    from_trough = round((latest - trough) / trough * 100, 1) if (trough and latest) else None
    jeonse_dep = [r.deposit for r in rows_area if r.deal_type == "jeonse" and r.deposit]
    jeonse_ratio = (round(median(jeonse_dep) / median_p * 100, 1)
                    if (jeonse_dep and median_p) else None)
    pys = [_pyeong_unit(r.deal_amount, area) for r in trades if r.exclusive_area]
    ppm = round(median(pys)) if pys else None
    monthly: dict = {}
    for r in trades:
        if r.contract_date:
            monthly.setdefault(_month_key(r.contract_date), []).append(r.deal_amount)
    ts = [{"month": k, "avg": round(mean(v)), "count": len(v)} for k, v in sorted(monthly.items())]
    recent = sorted(rows_area, key=lambda r: (r.contract_date or date.min), reverse=True)[:8]
    recent_out = [_tx_out(r, ppm) for r in recent]
    return {
        "area": area, "label": f"{area:g}㎡", "trade_count": len(trades),
        "reliability": _reliability(len(trades)),
        "latest_amount": latest, "price_median": median_p,
        "price_min": trough, "price_max": peak,
        "from_peak_pct": from_peak, "from_trough_pct": from_trough,
        "jeonse_ratio": jeonse_ratio, "ppm_median": ppm,
        "amounts": sorted(r.deal_amount for r in trades),
        "timeseries": ts, "recent": recent_out,
    }


@stat_cached()
def affordable_complexes(db: Session, max_price: int, property_type: str | None = "apartment",
                         limit: int = 24, lawd_cds: list[str] | None = None) -> list[dict]:
    """매매가 중앙값이 예산(max_price) 이하인 단지 목록. 예산 내 비싼 순(가까운 순).
    property_type='all'/None → 전 유형. lawd_cds 지정 시 해당 구만(관심 지역 필터)."""
    codes = set(str(c) for c in lawd_cds) if lawd_cds else None
    rows = [r for r in _load(db, property_type)
            if r.deal_type == "trade" and r.deal_amount and r.complex_name
            and (codes is None or str(r.lawd_cd) in codes)]
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r.complex_name, r.lawd_cd, r.property_type), []).append(r)
    out = []
    for (name, lawd, ptype), rs in groups.items():
        amts = sorted(x.deal_amount for x in rs)
        med = amts[len(amts) // 2]
        if med > max_price:
            continue
        latest = max(rs, key=lambda r: (r.contract_date or date.min))
        out.append({
            "name": name, "lawd_cd": lawd, "gu": _gu_name(lawd),
            "property_type": ptype,
            "median_price": med, "latest_amount": latest.deal_amount,
            "trade_count": len(rs),
            "build_year": next((x.build_year for x in rs if x.build_year), None),
            "contains_sample_data": any(x.is_sample for x in rs),
        })
    out.sort(key=lambda c: -c["median_price"])
    return out[:limit]


@stat_cached()
def compare_one(db: Session, name: str, lawd_cd: str, property_type: str = "apartment") -> dict:
    """비교용 단지 요약(경량). 거래 없으면 found=False. 누락값은 None(왜곡 방지)."""
    rows = [r for r in _load(db, property_type)
            if r.complex_name == name and r.lawd_cd == lawd_cd]
    trades = [r for r in rows if r.deal_type == "trade" and r.deal_amount]
    gu = _gu_name(lawd_cd)
    if not trades:
        return {"found": False, "name": name, "lawd_cd": lawd_cd, "gu": gu,
                "property_type": property_type}
    tamts = sorted(r.deal_amount for r in trades)
    latest = max(trades, key=lambda r: (r.contract_date or date.min)).deal_amount
    median_amt = tamts[len(tamts) // 2]
    peak = tamts[-1]
    from_peak = round((latest - peak) / peak * 100, 1) if peak else None
    ppm = sorted(_pyeong_unit(r.deal_amount, r.exclusive_area)
                 for r in trades if r.exclusive_area)
    ppm_med = round(ppm[len(ppm) // 2]) if ppm else None
    jeo = sorted(r.deposit for r in rows if r.deal_type == "jeonse" and r.deposit)
    jeo_med = jeo[len(jeo) // 2] if jeo else None
    jratio = round(jeo_med / median_amt * 100) if (jeo_med and median_amt) else None
    cx = db.scalar(select(Complex).where(Complex.name == name, Complex.lawd_cd == lawd_cd))
    build_year = (cx.build_year if (cx and cx.build_year) else
                  next((r.build_year for r in trades if r.build_year), None))
    dong = next((r.dong_name for r in rows if r.dong_name), None)
    return {
        "found": True, "name": name, "lawd_cd": lawd_cd, "gu": gu, "dong": dong,
        "property_type": property_type,
        "latest_amount": latest, "median_amount": median_amt,
        "ppm_median": ppm_med, "jeonse_ratio": jratio, "from_peak_pct": from_peak,
        "trade_count": len(trades),
        "build_year": build_year,
        "households": (cx.households if cx else None),
        "contains_sample_data": any(r.is_sample for r in rows),
    }


def rent_gap_signal(jeonse_ratio: float | None) -> dict | None:
    """전세가율(전세보증금 중앙값/매매가 중앙값)을 실수요자 관점 '참고 신호'로 해석.
    ⚠️ 왜곡 없음: 가격 예측·역전세 '단정' 금지. 전세가율의 의미(갭 크기·주의점)를 수치와 함께 설명만.
    청주는 갭투자·역전세가 큰 화두라 세입자·매수자·집주인 모두에게 유용한 맥락."""
    if jeonse_ratio is None:
        return None
    jr = jeonse_ratio
    if jr >= 85:
        level, gap = "high", "매우 작음"
        note = ("전세를 끼면 소액으로 매수할 수 있는 반면, 매매가가 내리면 전세금 반환이 "
                "어려워지는 역전세·깡통전세 위험도 커집니다. 계약 시 보증금 보호(HUG 보증 등)를 확인하세요.")
    elif jr >= 75:
        level, gap = "elevated", "작음"
        note = "매매가와 전세가 차이(갭)가 작은 편입니다. 소액 투자엔 유리하나 시세·입주물량 변화에 유의하세요."
    elif jr >= 60:
        level, gap = "normal", "보통"
        note = "매매가와 전세가 차이가 보통 수준입니다."
    else:
        level, gap = "low", "큼"
        note = "전세가율이 낮아 갭(실투자금)이 큽니다. 전세가 대비 매매가 여유는 상대적으로 큰 편입니다."
    return {"jeonse_ratio": jr, "level": level, "gap_label": gap, "note": note}


@stat_cached()
def complex_detail(db: Session, name: str, lawd_cd: str, property_type: str | None = None) -> dict:
    """(아파트×면적) 단지 상세: 최근가·중앙값·전저점/전고점·전세가율(rent_signal)·추이·거래량·최근거래."""
    q = select(Transaction).where(Transaction.complex_name == name,
                                  Transaction.lawd_cd == lawd_cd,
                                  Transaction.is_canceled.isnot(True))  # 해제분 제외
    if property_type:
        q = q.where(Transaction.property_type == property_type)
    rows = db.scalars(q).all()
    if not rows and property_type:
        # 유형 힌트로 0건이면 유형을 무시하고 name+lawd_cd 로 재조회(클릭 진입 견고성 — 잘못된 유형 힌트 대비)
        q2 = select(Transaction).where(Transaction.complex_name == name,
                                       Transaction.lawd_cd == lawd_cd,
                                       Transaction.is_canceled.isnot(True))
        rows = db.scalars(q2).all()
    if not rows:
        return {"found": False, "name": name, "gu": _gu_name(lawd_cd)}

    trades = [r for r in rows if r.deal_type == "trade" and r.deal_amount]

    # 월별 평균 매매가(추이) + 거래량
    monthly: dict[str, list[int]] = {}
    for r in trades:
        if r.contract_date:
            monthly.setdefault(_month_key(r.contract_date), []).append(r.deal_amount)
    timeseries = [{"month": k, "avg": round(mean(v)), "count": len(v)}
                  for k, v in sorted(monthly.items())]
    volume = [{"month": k, "count": len(v)} for k, v in sorted(monthly.items())]

    # ----- '현재 시세' 지표는 최근 N개월(집계 윈도우)만 사용. 추이(timeseries)는 전체 이력 -----
    cut = _cutoff_date()
    trades_recent = [r for r in trades if r.contract_date and r.contract_date >= cut]
    rows_recent = [r for r in rows if r.contract_date and r.contract_date >= cut]

    # 최근 N개월 고점 대비
    peak = max((r.deal_amount for r in trades_recent), default=None)
    latest_tx = max(trades_recent, key=lambda r: (r.contract_date or date.min)) if trades_recent else None
    latest_amount = latest_tx.deal_amount if latest_tx else None
    from_peak_pct = (round((latest_amount - peak) / peak * 100, 1)
                     if (peak and latest_amount and peak) else None)
    # 최근 N개월 저점 대비
    trough = min((r.deal_amount for r in trades_recent), default=None)
    from_trough_pct = (round((latest_amount - trough) / trough * 100, 1)
                       if (trough and latest_amount) else None)
    amts = sorted(r.deal_amount for r in trades_recent)
    price_min, price_max = (amts[0], amts[-1]) if amts else (None, None)
    price_median = round(median(amts)) if amts else None

    # 전세가율(갭) = 전세 보증금 중앙값 / 매매가 중앙값 (최근 N개월)
    jeonse_dep = [r.deposit for r in rows_recent if r.deal_type == "jeonse" and r.deposit]
    jeonse_ratio = (round(median(jeonse_dep) / price_median * 100, 1)
                    if (jeonse_dep and price_median) else None)

    # 층 프리미엄: 저층(1~5)/중층(6~15)/고층(16+) 평단가(만원/평) 평균
    bands = [("저층 (1~5층)", 1, 5), ("중층 (6~15층)", 6, 15), ("고층 (16층~)", 16, 10**9)]
    floor_bands = []
    for label, lo, hi in bands:
        ppm = [_pyeong_unit(r.deal_amount, r.exclusive_area) for r in trades_recent
               if r.floor and lo <= r.floor <= hi and r.exclusive_area]
        if ppm:
            floor_bands.append({"label": label, "avg_pyeong": round(mean(ppm)), "count": len(ppm)})

    # (아파트 × 면적) 면적별 상세 블록 — 근소한 전용면적 차이(예: 76.3㎡·76.6㎡)는
    # 같은 '평형'으로 병합(round(평) 기준). 대표 전용면적은 그룹 중앙값.
    area_groups: dict = {}
    for r in rows_recent:
        if r.exclusive_area:
            area_groups.setdefault(round(r.exclusive_area / PYEONG), []).append(r)
    areas = []
    for _py, rs in sorted(area_groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        rep_area = round(median([x.exclusive_area for x in rs]), 1)
        areas.append(_area_block(rep_area, rs))
    area_ppm = {a["area"]: a["ppm_median"] for a in areas}

    # 최근 실거래(전 거래유형) — 같은 평형 중앙 평단가 기준 이상치 플래그
    recent = sorted(rows, key=lambda r: (r.contract_date or date.min), reverse=True)[:12]
    recent_out = [_tx_out(r, area_ppm.get(round(r.exclusive_area, 1)) if r.exclusive_area else None)
                  for r in recent]

    # 해제(취소) 건수 — 최근 N개월(시세 왜곡 방지 차원에서 별도 노출)
    cq = select(Transaction).where(Transaction.complex_name == name,
                                   Transaction.lawd_cd == lawd_cd,
                                   Transaction.is_canceled.is_(True))
    if property_type:
        cq = cq.where(Transaction.property_type == property_type)
    canceled_count = sum(1 for r in db.scalars(cq).all()
                         if r.contract_date and r.contract_date >= cut)

    # 메타 + 좌표
    cx = db.scalar(select(Complex).where(Complex.name == name, Complex.lawd_cd == lawd_cd))
    dong = next((r.dong_name for r in rows if r.dong_name), None)
    build_year = (cx.build_year if (cx and cx.build_year) else
                  next((r.build_year for r in trades if r.build_year), None))

    # 단지 vs 동네(구) 평단가 포지셔닝 — 하이퍼로컬 차별화. 평단가(만원/평)로 공정 비교.
    ptype = property_type or (rows[0].property_type if rows else "apartment")
    cx_ppm = [_pyeong_unit(r.deal_amount, r.exclusive_area)
              for r in trades_recent if r.exclusive_area and r.deal_amount]
    cx_ppm_med = round(median(cx_ppm)) if cx_ppm else None
    vs_region = None
    if cx_ppm_med:
        gu_rows = _rows_where(db,
                              Transaction.property_type == ptype,
                              Transaction.lawd_cd == lawd_cd,
                              Transaction.contract_date >= cut,
                              Transaction.deal_type == "trade",
                              Transaction.is_canceled.isnot(True))
        gu_ppm = [_pyeong_unit(r.deal_amount, r.exclusive_area)
                  for r in gu_rows if r.exclusive_area and r.deal_amount]
        gu_ppm_med = round(median(gu_ppm)) if gu_ppm else None
        if gu_ppm_med:
            vs_region = {"complex_ppm": cx_ppm_med, "gu_ppm": gu_ppm_med,
                         "gu": _gu_name(lawd_cd),
                         "pct": round((cx_ppm_med - gu_ppm_med) / gu_ppm_med * 100, 1),
                         "sample": len(gu_ppm)}

    return {
        "found": True,
        "vs_region": vs_region,
        "name": name, "gu": _gu_name(lawd_cd), "dong": dong,
        "property_type": property_type or (rows[0].property_type if rows else None),
        "build_year": build_year,
        "lat": cx.lat if cx else None, "lng": cx.lng if cx else None,
        "latest_amount": latest_amount, "peak_amount": peak, "from_peak_pct": from_peak_pct,
        "trough_amount": trough, "from_trough_pct": from_trough_pct,
        "price_min": price_min, "price_max": price_max, "price_median": price_median,
        "jeonse_ratio": jeonse_ratio, "floor_bands": floor_bands,
        "rent_signal": rent_gap_signal(jeonse_ratio),
        "trade_count": len(trades_recent),
        "reliability": _reliability(len(trades_recent)),
        "canceled_count": canceled_count,
        "complex_meta": ({
            "households": cx.households, "dong_count": cx.dong_count,
            "approval_date": cx.approval_date, "heating": cx.heating,
            "total_area": cx.total_area, "builder": cx.builder, "parking": cx.parking,
            "price_official": cx.price_official, "price_basis_date": cx.price_basis_date,
            "source": cx.meta_source,
        } if cx and (cx.meta_source or cx.price_official) else None),
        "timeseries": timeseries, "volume": volume,
        "areas": areas,
        "recent": recent_out,
        "contains_sample_data": any(r.is_sample for r in rows),
    }


@stat_cached()
def heatmap(db: Session, property_type: str = "apartment") -> dict:
    """단지별 평단가(만원/평) 중앙값 + 좌표 → 지도 히트맵용. 좌표 없는 단지는 제외(왜곡 방지)."""
    rows = [r for r in _load(db, property_type)
            if r.deal_type == "trade" and r.deal_amount and r.exclusive_area and r.complex_name]
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r.complex_name, r.lawd_cd), []).append(r)
    cmap = {(c.name, c.lawd_cd): (c.lat, c.lng)
            for c in db.scalars(select(Complex).where(Complex.lat.isnot(None)))}
    pts = []
    for (name, lawd), rs in groups.items():
        c = cmap.get((name, lawd))
        if not c:
            continue
        pys = [_pyeong_unit(x.deal_amount, x.exclusive_area) for x in rs]
        pts.append({
            "complex_name": name, "lawd_cd": lawd, "gu": _gu_name(lawd),
            "dong": rs[0].dong_name, "property_type": property_type,
            "lat": c[0], "lng": c[1],
            "median_pyeong": round(median(pys)), "count": len(rs),
        })
    pts.sort(key=lambda x: x["median_pyeong"], reverse=True)
    vals = [p["median_pyeong"] for p in pts]
    # 구 단위 집계(좌표 불필요 — 지오코딩 없이도 항상 표시 가능)
    gu_groups: dict[str, list] = {}
    for r in rows:
        gu_groups.setdefault(r.lawd_cd, []).append(_pyeong_unit(r.deal_amount, r.exclusive_area))
    districts = []
    for code, pys in gu_groups.items():
        c = DISTRICT_CENTROIDS.get(code)
        if not c or not pys:
            continue
        districts.append({
            "lawd_cd": code, "gu": _gu_name(code), "lat": c[0], "lng": c[1],
            "median_pyeong": round(median(pys)), "count": len(pys), "level": "district",
        })
    districts.sort(key=lambda x: x["median_pyeong"], reverse=True)
    dvals = [d["median_pyeong"] for d in districts]
    return {"points": pts, "districts": districts,
            "district_min": min(dvals) if dvals else None,
            "district_max": max(dvals) if dvals else None,
            "min_pyeong": min(vals) if vals else None,
            "max_pyeong": max(vals) if vals else None, "total": len(pts)}


@stat_cached()
def map_markers(db: Session, deal_type: str = "trade", property_type: str = "apartment") -> dict:
    """지도용 단지 마커 — 거래유형별 대표가(중앙값) + 좌표. 좌표 없는 단지는 제외(왜곡 방지).

    - trade: 평단가(만원/평) 중앙값 + 매매가 중앙값. value=평단가.
    - jeonse/wolse: 보증금 중앙값(+월세 중앙값). value=보증금.
    표본이 없는 단지는 제외. 색 구간(bands)은 value의 20/40/60/80 분위 → 프런트 색 결정용.
    """
    dt = deal_type if deal_type in ("trade", "jeonse", "wolse") else "trade"
    rows = [r for r in _load(db, property_type)
            if r.deal_type == dt and r.complex_name and not r.is_canceled]
    # (이름, 구, 동) 단위 그룹 — 같은 구 동명(同名) 단지(예: 흥덕구 '대원' 가경동/복대동)가
    # 1개 마커로 합쳐지면 좌표·동 표기가 임의로 섞이고 중앙값도 두 단지 혼합(v1.224 교정).
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r.complex_name, r.lawd_cd, r.dong_name), []).append(r)
    dong_n: dict[tuple, int] = {}   # (이름, 구) → 동 개수(모호성 판별)
    for (name, lawd, _d) in groups:
        dong_n[(name, lawd)] = dong_n.get((name, lawd), 0) + 1
    cmap_dong: dict[tuple, tuple] = {}
    cmap_legacy: dict[tuple, tuple] = {}
    for c in db.scalars(select(Complex).where(Complex.lat.isnot(None))):
        if c.dong is not None:
            cmap_dong[(c.name, c.lawd_cd, c.dong)] = (c.lat, c.lng)
        else:
            cmap_legacy[(c.name, c.lawd_cd)] = (c.lat, c.lng)
    markers = []
    for (name, lawd, dong), rs in groups.items():
        # 좌표: 동 일치 행 우선. 없으면 레거시(dong=None) 좌표는 '동이 유일'할 때만 —
        # 복수 동이면 어느 단지 좌표인지 알 수 없어 제외(disclaimer 의 '좌표 미확인 제외').
        c = cmap_dong.get((name, lawd, dong))
        if not c and dong_n.get((name, lawd), 0) <= 1:
            c = cmap_legacy.get((name, lawd))
        if not c:
            continue
        # 지도 필터용 부가 속성(왜곡 없음 — 실거래 행에서 도출, 없으면 None/빈 목록)
        bys = [x.build_year for x in rs if x.build_year]
        m = {"complex_name": name, "lawd_cd": lawd, "gu": _gu_name(lawd),
             "dong": dong, "property_type": property_type,
             "deal_type": dt, "lat": c[0], "lng": c[1], "count": len(rs),
             "build_year": max(set(bys), key=bys.count) if bys else None,   # 최빈 건축년도
             "area_bands": sorted({b for b in (_bucket(x.exclusive_area) for x in rs) if b}),
             "is_sample": any(getattr(x, "is_sample", False) for x in rs)}
        if dt == "trade":
            pys = [_pyeong_unit(x.deal_amount, x.exclusive_area)
                   for x in rs if x.deal_amount and x.exclusive_area]
            amts = [x.deal_amount for x in rs if x.deal_amount]
            if not pys:
                continue
            m["median_pyeong"] = round(median(pys))
            m["median_amount"] = round(median(amts)) if amts else None
            m["value"] = m["median_pyeong"]
        else:
            deps = [x.deposit for x in rs if x.deposit]
            if not deps:
                continue
            m["median_deposit"] = round(median(deps))
            m["value"] = m["median_deposit"]
            if dt == "wolse":
                rents = [x.monthly_rent for x in rs if x.monthly_rent]
                m["median_monthly"] = round(median(rents)) if rents else None
        markers.append(m)
    markers.sort(key=lambda x: x["value"], reverse=True)
    vals = sorted(m["value"] for m in markers)
    bands = [vals[int(len(vals) * p)] for p in (0.2, 0.4, 0.6, 0.8)] if vals else []
    summary = {"count": len(markers),
               "median": round(median(vals)) if vals else None,
               "avg": round(mean(vals)) if vals else None}
    return {"deal_type": dt, "property_type": property_type,
            "markers": markers, "count": len(markers), "bands": bands,
            "summary": summary,
            "min": vals[0] if vals else None, "max": vals[-1] if vals else None}


@stat_cached()
def newly_low(db: Session, property_type: str = "apartment", limit: int = 8) -> list[dict]:
    """신고가: 단지×면적대 그룹에서 최근월 최저가가 '이전 모든 달의 최저가'보다 낮은 경우.
    이전 기록이 없으면(거래 1개월뿐) 제외 — 신고가를 지어내지 않는다."""
    groups: dict[tuple, dict] = {}
    for r in _load(db, property_type):
        if r.deal_type != "trade" or not r.deal_amount or not r.contract_date or not r.complex_name:
            continue
        b = _bucket(r.exclusive_area)
        g = groups.setdefault((r.complex_name, b),
                              {"gu": r.lawd_cd, "months": {}, "is_sample": False, "bucket": b})
        g["months"].setdefault(_month_key(r.contract_date), []).append(r.deal_amount)
        g["is_sample"] = g["is_sample"] or r.is_sample

    blabel = {k: l for k, l, _lo, _hi in AREA_BUCKETS}
    out = []
    for (name, b), g in groups.items():
        keys = sorted(g["months"])
        if len(keys) < 2:
            continue
        latest = keys[-1]
        latest_min = min(g["months"][latest])
        prev_low = min(v for k in keys[:-1] for v in g["months"][k])
        if latest_min < prev_low:
            out.append({
                "complex_name": name, "gu": _gu_name(g["gu"]),
                "area_label": blabel.get(b, "-"),
                "latest_amount": latest_min, "prev_low": prev_low,
                "change_pct": round((latest_min - prev_low) / prev_low * 100, 1),
                "month": latest, "is_sample": g["is_sample"],
            })
    out.sort(key=lambda x: x["change_pct"])
    return out[:limit]


@stat_cached()
def city_trend(db: Session, property_type: str = "apartment", months: int = 12) -> dict:
    """청주 전체(구 통합) 월별 매매가 중앙값 시계열. 빈 달은 None(미보간)."""
    today = date.today().replace(day=1)
    keys: list[str] = []
    y, m = today.year, today.month
    for _ in range(months):
        keys.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys = list(reversed(keys))
    monthly: dict[str, list] = {}
    sample = False
    for r in _load(db, property_type):
        if r.deal_type == "trade" and r.deal_amount and r.contract_date:
            monthly.setdefault(_month_key(r.contract_date), []).append(r.deal_amount)
            sample = sample or r.is_sample
    values = [round(median(monthly[k])) if monthly.get(k) else None for k in keys]
    return {"months": keys, "values": values, "contains_sample_data": sample}


@stat_cached()
def gu_price_ranking(db: Session, property_type: str = "apartment") -> list[dict]:
    """구별 매매가/평단가 랭킹(평단가 중앙값 내림차순) + 최근월 거래량."""
    # 전체 최신월 산출(구간 비교 일관성)
    all_months = []
    for r in _load(db, property_type):
        if r.deal_type == "trade" and r.contract_date:
            all_months.append(_month_key(r.contract_date))
    latest_month = max(all_months) if all_months else None
    out = []
    for d in CHEONGJU_DISTRICTS:
        rows = _rows_where(
            db,
            Transaction.property_type == property_type,
            Transaction.lawd_cd == d.code,
            Transaction.contract_date >= _cutoff_date(16),  # 최근 16개월
            Transaction.deal_type == "trade",
            Transaction.is_canceled.isnot(True))  # 해제분 제외
        amts = [r.deal_amount for r in rows if r.deal_amount]
        pys = [_pyeong_unit(r.deal_amount, r.exclusive_area)
               for r in rows if r.deal_amount and r.exclusive_area]
        month_count = sum(1 for r in rows
                          if r.contract_date and _month_key(r.contract_date) == latest_month)
        out.append({
            "code": d.code, "name": f"청주시 {d.name}", "gu": d.name,
            "median_mae": round(median(amts)) if amts else None,
            "median_pyeong": round(median(pys)) if pys else None,
            "count": len(amts), "month_count": month_count, "month": latest_month,
            "low_sample": len(amts) < LOW_SAMPLE_THRESHOLD,
        })
    out.sort(key=lambda x: (x["median_pyeong"] is None, -(x["median_pyeong"] or 0)))
    return out


@stat_cached()
def recent_trades(db: Session, property_type: str = "apartment", per_gu: int = 4) -> list[dict]:
    """구별 최신 매매 실거래 N건씩 + 신고가(is_high) 표시."""
    out = []
    for d in CHEONGJU_DISTRICTS:
        rows = [r for r in _rows_where(
            db,
            Transaction.property_type == property_type,
            Transaction.lawd_cd == d.code,
            Transaction.contract_date >= _cutoff_date(60),  # 최근 5년(신고가 판정·메모리)
            Transaction.deal_type == "trade",
            Transaction.is_canceled.isnot(True)) if r.deal_amount]
        # 단지×면적대별 최고가/표본수 → 신고가 판정
        groups: dict[tuple, list] = {}
        for r in rows:
            groups.setdefault((r.complex_name, _bucket(r.exclusive_area)), []).append(r.deal_amount)
        rows.sort(key=lambda r: (r.contract_date or date.min), reverse=True)
        window = rows[:12]                                   # 최근 거래 윈도
        window.sort(key=lambda r: r.deal_amount, reverse=True)  # 그 안에서 가격순
        items = []
        for r in window[:per_gu]:
            g = groups.get((r.complex_name, _bucket(r.exclusive_area)), [])
            is_high = bool(r.complex_name) and len(g) >= 2 and r.deal_amount >= max(g)
            items.append({
                "complex_name": r.complex_name, "lawd_cd": r.lawd_cd,
                "property_type": r.property_type, "dong": r.dong_name,
                "exclusive_area": r.exclusive_area, "floor": r.floor,
                "contract_date": r.contract_date.isoformat() if r.contract_date else None,
                "deal_amount": r.deal_amount, "is_high": is_high, "is_sample": r.is_sample,
            })
        out.append({"gu": d.name, "name": f"청주시 {d.name}", "code": d.code, "items": items})
    return out


# ---------------- 가격 분포 히스토그램 ----------------
_DIST_MIN_SAMPLES = 8  # 표본 부족 시 분포 미산출(왜곡 방지)


def _percentile(sorted_vals: list[int], p: float):
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    if f >= len(sorted_vals) - 1:
        return sorted_vals[-1]
    frac = k - f
    return round(sorted_vals[f] * (1 - frac) + sorted_vals[f + 1] * frac)


def _choose_width(lo: int, hi: int, deal_type: str) -> int:
    span = max(hi - lo, 1)
    cands = [10, 20, 50, 100, 200] if deal_type == "wolse" else \
            [2500, 5000, 10000, 20000, 50000, 100000]  # 만원 (0.25~10억)
    for w in cands:
        if span / w <= 12:
            return w
    return cands[-1]


@stat_cached()
def price_distribution(db: Session, property_type: str = "apartment",
                       deal_type: str = "trade", gu: str | None = None,
                       area_band: str = "all") -> dict:
    """거래금액(매매=deal_amount / 전세=deposit / 월세=monthly_rent) 분포.
    표본 < 8 이면 buckets=None(표본 부족). 모든 수치는 실데이터에서만 산출."""
    field = {"trade": "deal_amount", "jeonse": "deposit",
             "wolse": "monthly_rent"}.get(deal_type, "deal_amount")
    rows = _band_rows(_load(db, property_type), area_band)
    if gu:
        rows = [r for r in rows if r.lawd_cd == gu]
    vals = sorted(v for r in rows if (v := getattr(r, field, None)) and v > 0)
    unit = "만원/월" if deal_type == "wolse" else "만원"
    base = {"deal_type": deal_type, "property_type": property_type,
            "gu": gu, "area_band": area_band, "unit": unit, "count": len(vals)}
    if len(vals) < _DIST_MIN_SAMPLES:
        return {**base, "insufficient": True, "buckets": None,
                "median": None, "p25": None, "p75": None, "min": None, "max": None}
    lo, hi = vals[0], vals[-1]
    width = _choose_width(lo, hi, deal_type)
    start = (lo // width) * width
    buckets = []
    edge = start
    while edge <= hi:
        nxt = edge + width
        cnt = sum(1 for v in vals if edge <= v < nxt or (nxt > hi and v == hi and edge <= v))
        buckets.append({"lo": edge, "hi": nxt, "count": cnt})
        edge = nxt
    return {**base, "insufficient": False, "bucket_width": width,
            "buckets": buckets,
            "median": _percentile(vals, 0.5),
            "p25": _percentile(vals, 0.25), "p75": _percentile(vals, 0.75),
            "min": lo, "max": hi}


@stat_cached()
def trending_complexes(db: Session, property_type: str = "apartment", limit: int = 8) -> dict:
    """'거래 급상승' — 최근 90일 거래량이 직전 90일 대비 늘어난 단지(실제 신호, 왜곡 없음).

    조회수·관심수 같은 사용자 데이터는 아직 신뢰표본이 없어 쓰지 않는다.
    급상승(delta>0) 표본이 3건 미만이면 '거래 활발'(최근 거래량 순)로 폴백.
    반환: {basis: 'surge'|'active', items:[{rank,name,lawd_cd,gu,property_type,
           recent_count,prev_count,delta,price,contains_sample_data}]}
    """
    from datetime import timedelta
    rows = [r for r in _load_window(db, property_type, 8)
            if r.deal_type == "trade" and r.deal_amount and r.complex_name and r.contract_date]
    if not rows:
        return {"basis": "surge", "items": []}
    ref = max(r.contract_date for r in rows)        # 데이터 지연 대비: 최신 계약일 기준
    recent_cut = ref - timedelta(days=90)
    prev_cut = ref - timedelta(days=180)
    groups: dict = {}
    for r in rows:
        groups.setdefault((r.complex_name, r.lawd_cd), []).append(r)
    out = []
    for (name, code), rs in groups.items():
        recent = [x for x in rs if x.contract_date > recent_cut]
        prev = [x for x in rs if prev_cut < x.contract_date <= recent_cut]
        rc = len(recent)
        if rc < 2:                                   # 최소 표본(노이즈 방지)
            continue
        out.append({
            "name": name, "lawd_cd": code, "gu": _gu_name(code),
            "dong": next((x.dong_name for x in recent if x.dong_name), None),
            "property_type": rs[0].property_type,
            "recent_count": rc, "prev_count": len(prev), "delta": rc - len(prev),
            "price": int(median([x.deal_amount for x in recent])),
            "contains_sample_data": any(x.is_sample for x in rs),
        })
    surge = [o for o in out if o["delta"] > 0]
    if len(surge) >= 3:
        surge.sort(key=lambda o: (-o["delta"], -o["recent_count"]))
        res, basis = surge, "surge"
    else:
        out.sort(key=lambda o: (-o["recent_count"], -o["delta"]))
        res, basis = out, "active"
    res = res[:limit]
    for i, o in enumerate(res, 1):
        o["rank"] = i
    return {"basis": basis, "items": res}


@stat_cached()
def top_movers(db: Session, property_type: str = "apartment", limit: int = 10) -> dict:
    """'최고 상승·하락 아파트' — 같은 단지·평형에서 **직전 거래 대비** 실거래가가
    가장 많이 오른/내린 순위. 단지+평(전용면적 반올림)별로 최근 2건을 비교(왜곡 없음).

    반환: {up:[...], down:[...]}, 각 항목 {rank,name,area_py,gu,dong,lawd_cd,
           prev_amount,latest_amount,change,pct,latest_date,contains_sample_data}
    """
    rows = [r for r in _load_window(db, property_type, 60)
            if r.deal_type == "trade" and r.deal_amount and r.complex_name
            and r.contract_date and r.exclusive_area]
    groups: dict = {}
    for r in rows:
        py = round(r.exclusive_area / PYEONG)
        groups.setdefault((r.complex_name, r.lawd_cd, py), []).append(r)
    movers = []
    for (name, code, py), rs in groups.items():
        if len(rs) < 2:
            continue
        rs.sort(key=lambda x: (x.contract_date, x.deal_amount))
        prev, latest = rs[-2], rs[-1]
        if not prev.deal_amount:
            continue
        change = latest.deal_amount - prev.deal_amount
        if change == 0:
            continue
        movers.append({
            "name": name, "area_py": py, "lawd_cd": code, "gu": _gu_name(code),
            "dong": latest.dong_name,
            "prev_amount": prev.deal_amount, "latest_amount": latest.deal_amount,
            "change": change, "pct": round(change / prev.deal_amount * 100, 1),
            "latest_date": latest.contract_date.isoformat() if latest.contract_date else None,
            "contains_sample_data": any(x.is_sample for x in rs),
        })

    def _rank(lst):
        for i, o in enumerate(lst, 1):
            o["rank"] = i
        return lst
    ups = _rank(sorted([m for m in movers if m["change"] > 0],
                       key=lambda m: m["pct"], reverse=True)[:limit])
    downs = _rank(sorted([m for m in movers if m["change"] < 0],
                         key=lambda m: m["pct"])[:limit])
    return {"up": ups, "down": downs}


@stat_cached()
def price_overview(db: Session, lawd_cd: str | None = None,
                   property_type: str = "apartment", band: str = "all") -> dict:
    """시세 탭(지역→단지) 서버 집계. 클라이언트 500건 집계를 대체(확장성).

    윈도우=최근 aggregate_months. 해제분 제외, 표본(is_sample)은 포함하되 배지.
    band: all|small(<60㎡)|medium(60~85)|large(>=85㎡).
    반환: {gu, property_type, summary:{median,ratio,count,dM}, complexes:[...]}
    """
    codes = {str(lawd_cd)} if lawd_cd else None

    def _band(a):
        if a is None:
            return "na"
        return "small" if a < 60 else "medium" if a < 85 else "large"

    rows = [r for r in _load(db, property_type)
            if not r.is_canceled and r.complex_name
            and (codes is None or str(r.lawd_cd) in codes)
            and (band == "all" or _band(r.exclusive_area) == band)]
    trades = [r for r in rows if r.deal_type == "trade" and r.deal_amount]
    jeon = [r.deposit for r in rows if r.deal_type == "jeonse" and r.deposit]
    amts = [r.deal_amount for r in trades]
    mtr = round(median(amts)) if amts else None
    mje = round(median(jeon)) if jeon else None

    monthly: dict = {}
    for r in trades:
        monthly.setdefault(_month_key(r.contract_date), []).append(r.deal_amount)
    keys = sorted(monthly)
    d_m = None
    if len(keys) >= 2:
        a, b = median(monthly[keys[-1]]), median(monthly[keys[-2]])
        if a and b:
            d_m = round((a - b) / b * 100, 1)

    g: dict = {}
    for r in trades:
        o = g.setdefault((r.complex_name, r.lawd_cd), {
            "name": r.complex_name, "lawd_cd": r.lawd_cd, "gu": _gu_name(r.lawd_cd),
            "dong": r.dong_name, "ptype": r.property_type, "amts": [], "last": None, "sample": False})
        o["amts"].append(r.deal_amount)
        if r.contract_date and (o["last"] is None or r.contract_date > o["last"]):
            o["last"] = r.contract_date
        if not o["dong"] and r.dong_name:
            o["dong"] = r.dong_name
        if r.is_sample:
            o["sample"] = True
    complexes = [{
        "name": o["name"], "lawd_cd": o["lawd_cd"], "gu": o["gu"], "dong": o["dong"],
        "property_type": o["ptype"], "median": round(median(o["amts"])), "count": len(o["amts"]),
        "last_date": o["last"].isoformat() if o["last"] else None,
        "contains_sample_data": o["sample"],
    } for o in g.values()]
    complexes.sort(key=lambda c: (-c["count"], -(c["median"] or 0)))
    return {
        "gu": _gu_name(lawd_cd) if lawd_cd else None,
        "property_type": property_type,
        "summary": {"median": mtr, "ratio": round(mje / mtr * 100, 1) if (mje and mtr) else None,
                    "count": len(trades), "dM": d_m},
        "complexes": complexes,
    }


@stat_cached()
def landmark_apts(db: Session, property_type: str = "apartment", limit: int = 5,
                  band: str = "all") -> list[dict]:
    """'대장아파트' TOP N — 단지별 대표 매매가(중앙값) 상위. band 지정 시 해당 평형만.
    최고가 1건이 아니라 단지의 매매 거래 '중앙값'으로 산정(이상치·표본 왜곡 방지)."""
    rows = [r for r in _load(db, property_type)
            if r.deal_type == "trade" and r.deal_amount and r.complex_name]
    rows = _band_rows(rows, band)
    groups: dict = {}
    for r in rows:
        groups.setdefault((r.complex_name, r.lawd_cd), []).append(r)
    out = []
    for (name, code), rs in groups.items():
        amts = [x.deal_amount for x in rs]
        areas = [x.exclusive_area for x in rs if x.exclusive_area]
        ppms = [round(x.deal_amount / (x.exclusive_area / PYEONG))
                for x in rs if x.exclusive_area]
        dongs = [x.dong_name for x in rs if x.dong_name]
        out.append({
            "name": name, "code": code, "gu": _gu_name(code),
            "dong": dongs[0] if dongs else None,
            "price": int(median(amts)),
            "ppm": int(median(ppms)) if ppms else None,
            "area": round(median(areas), 1) if areas else None,
            "count": len(rs),
        })
    out.sort(key=lambda x: x["price"], reverse=True)
    top = out[:limit]
    for i, o in enumerate(top, 1):
        o["rank"] = i
    return top


@stat_cached()
def landmark_by_band(db: Session, property_type: str = "apartment", each: int = 5) -> list[dict]:
    """대표 평형(소형/중형/대형)별 대장아파트."""
    return [{"key": k, "label": label, "items": landmark_apts(db, property_type, each, k)}
            for k, label, _lo, _hi in AREA_BUCKETS]


@stat_cached()
def recent_by_band(db: Session, property_type: str = "apartment", each: int = 5) -> list[dict]:
    """대표 평형별 최신 실거래(최근 윈도 → 가격순 상위). 신고가(is_high) 표시."""
    rows = [r for r in _load(db, property_type)
            if r.deal_type == "trade" and r.deal_amount]
    groups: dict = {}
    for r in rows:
        groups.setdefault((r.complex_name, _bucket(r.exclusive_area)), []).append(r.deal_amount)
    res = []
    for k, label, _lo, _hi in AREA_BUCKETS:
        brows = [r for r in rows if _bucket(r.exclusive_area) == k]
        brows.sort(key=lambda r: (r.contract_date or date.min), reverse=True)
        window = brows[:30]
        window.sort(key=lambda r: r.deal_amount, reverse=True)
        items = []
        for r in window[:each]:
            g = groups.get((r.complex_name, _bucket(r.exclusive_area)), [])
            is_high = bool(r.complex_name) and len(g) >= 2 and r.deal_amount >= max(g)
            items.append({
                "complex_name": r.complex_name, "lawd_cd": r.lawd_cd, "gu": _gu_name(r.lawd_cd),
                "property_type": r.property_type, "dong": r.dong_name,
                "exclusive_area": r.exclusive_area, "floor": r.floor,
                "contract_date": r.contract_date.isoformat() if r.contract_date else None,
                "deal_amount": r.deal_amount, "is_high": is_high, "is_sample": r.is_sample,
            })
        res.append({"key": k, "label": label, "items": items})
    return res


def complex_quotes(db: Session, items: list[dict]) -> dict:
    """여러 단지(관심/우리집 등)의 최근 매매가·전월대비를 한 번에 계산.
    한 쿼리로 조회 후 Python 그룹핑. 데이터 없으면 값 None(왜곡 없음)."""
    pairs = [(it.get("name"), it.get("lawd_cd"), it.get("property_type") or "apartment")
             for it in (items or []) if it.get("name") and it.get("lawd_cd")][:60]
    if not pairs:
        return {"quotes": []}
    names = {p[0] for p in pairs}
    lawds = {p[1] for p in pairs}
    rows = db.scalars(select(Transaction).where(
        Transaction.deal_type == "trade",
        Transaction.deal_amount.isnot(None),
        Transaction.is_canceled.isnot(True),
        Transaction.complex_name.in_(names),
        Transaction.lawd_cd.in_(lawds),
    )).all()
    groups: dict = {}
    for r in rows:
        groups.setdefault((r.complex_name, r.lawd_cd, r.property_type), []).append(r)
    out = []
    for (name, lawd, pt) in pairs:
        rs = groups.get((name, lawd, pt), [])
        latest = mom = None
        if rs:
            monthly: dict = {}
            for r in rs:
                if r.contract_date:
                    monthly.setdefault(_month_key(r.contract_date), []).append(r.deal_amount)
            ms = sorted(monthly)
            if ms:
                med = {m: median(monthly[m]) for m in ms}
                latest = round(med[ms[-1]])
                if len(ms) >= 2 and med[ms[-2]]:
                    mom = round((med[ms[-1]] - med[ms[-2]]) / med[ms[-2]] * 100, 1)
        out.append({"name": name, "lawd_cd": lawd, "property_type": pt,
                    "latest_amount": latest, "mom_pct": mom, "trade_count": len(rs)})
    return {"quotes": out}
