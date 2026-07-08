"""청주 전입자 온보딩 추천 — '청주가 처음이세요?'

전략: 아무것도 팔지 않는 앱이므로 '말릴 수 있다'. SK하이닉스·오송·오창 발령자 등
낯선 도시로 오는 신규 수요층에게 '직장 근처 + 시세 + 조심할 점'을 한 번에 큐레이션.

왜곡 없음:
- 새 데이터를 만들지 않고 기존 로직만 조립(통근검색 + complex_quotes).
- 통근시간=직선거리 기반 추정, 매매가=실거래 중앙값(참고용) 임을 notice로 명시.
- 예산은 '적합/부적합' 단정 대신 '자기자본 대비 차액(over_budget_by)'만 중립 제공
  (실제 구매력은 대출·심사로 달라지므로 판정하지 않음).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CommuteDestination, Complex
from app.services.commute import search_by_commute
from app.services.stats import complex_quotes


def _dest_options(db: Session) -> list[dict]:
    rows = db.scalars(select(CommuteDestination).where(
        CommuteDestination.is_active.is_(True),
        CommuteDestination.category == "job",
        CommuteDestination.lat.isnot(None),
    ).order_by(CommuteDestination.sort_order)).all()
    return [{"key": d.key, "name": d.name, "gu": d.gu} for d in rows]


def options(db: Session) -> dict:
    """온보딩 1단계 선택지(직장·산단). 시드 없으면 빈 목록(왜곡 없음)."""
    return {"destinations": _dest_options(db)}


def recommend(db: Session, dest_key: str, budget: int | None = None,
              has_kids: bool = False, mode: str = "driving",
              max_minutes: int = 30, limit: int = 8) -> dict:
    """직장(dest_key) 근처 단지에 최근가·전월대비·전세가율 신호를 얹어 큐레이션.
    budget(보유현금·만원)은 차액 표기에만 사용(적합 판정 아님)."""
    dest = db.scalar(select(CommuteDestination).where(CommuteDestination.key == dest_key))
    if not dest or dest.lat is None:
        return {"destination": None, "items": [],
                "notice": "선택한 거점 정보가 없습니다. 통근 거점 시드(seed_commute)가 필요합니다."}

    near = search_by_commute(db, dest.id, mode, max_minutes, property_type="apartment")
    results = (near.get("results") or [])[:40]
    if not results:
        return {"destination": {"key": dest.key, "name": dest.name},
                "budget": budget, "has_kids": bool(has_kids), "items": [],
                "notice": "주변 단지 데이터가 아직 없습니다. 실거래 수집·지오코딩 후 채워집니다."}

    ids = [r["complex_id"] for r in results]
    cxs = {c.id: c for c in db.scalars(select(Complex).where(Complex.id.in_(ids)))}
    items_in = [{"name": r["name"], "lawd_cd": cxs[r["complex_id"]].lawd_cd,
                 "property_type": r["property_type"]}
                for r in results if r["complex_id"] in cxs]
    quotes = {f'{q["name"]}|{q["lawd_cd"]}|{q["property_type"]}': q
              for q in complex_quotes(db, items_in)["quotes"]}

    out: list[dict] = []
    for r in results:
        cx = cxs.get(r["complex_id"])
        if not cx:
            continue
        q = quotes.get(f'{r["name"]}|{cx.lawd_cd}|{r["property_type"]}')
        price = q["latest_amount"] if q else None
        over = (price - budget) if (price is not None and budget) else None
        out.append({
            "name": r["name"], "gu": r["gu"], "lawd_cd": cx.lawd_cd,
            "property_type": r["property_type"], "minutes": r["minutes"],
            "lat": r["lat"], "lng": r["lng"],
            "latest_amount": price, "mom_pct": (q["mom_pct"] if q else None),
            "over_budget_by": over,   # 자기자본 대비 부족액(만원). 음수면 자기자본 이내. None=정보부족
        })
    # 정렬: 가격 정보 있는 것 우선 → 통근시간 짧은 순(직장 근처가 온보딩 핵심)
    out.sort(key=lambda x: (x["latest_amount"] is None, x["minutes"]))

    return {
        "destination": {"key": dest.key, "name": dest.name, "gu": dest.gu},
        "budget": budget, "has_kids": bool(has_kids),
        "items": out[:limit],
        "notice": ("통근시간은 직선거리 기반 추정, 최근 매매가는 실거래 중앙값(참고용)입니다. "
                   "‘자기자본 대비 차액’은 단순 비교이며 실제 구매력은 대출·심사로 달라집니다. "
                   "청집사는 중개·광고 수익이 없어 특정 매물을 권유하지 않습니다."),
    }
