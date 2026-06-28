"""통합 검색 — 단지/지역/매물을 한 번에.

- complexes: 실거래 단지명 매칭(대표 최근 매매가).
- regions: 청주 4개 구 + 법정동(dong_name) 매칭.
- listings: 등록 매물 제목/단지/동 매칭.
대중 진입점이므로 가볍고 빠르게(각 그룹 상한). 왜곡 방지: 실거래·등록매물 분리 표기.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Transaction, Listing
from app.services.stats import _gu_name
from app.data.region_codes import CHEONGJU_DISTRICTS

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(q: str = Query("", description="검색어"),
          db: Session = Depends(get_db)):
    q = (q or "").strip()
    if len(q) < 1:
        return {"q": q, "complexes": [], "regions": [], "listings": []}
    like = f"%{q}%"   # 선두 와일드카드: PostgreSQL은 pg_trgm GIN 인덱스(0016)가 가속, SQLite는 스캔

    # --- 단지(실거래 기준, 최근 거래 우선 dedup) ---
    rows = db.scalars(
        select(Transaction).where(
            Transaction.complex_name.like(like),
            Transaction.deal_type == "trade",
            Transaction.is_canceled.isnot(True),
        ).order_by(Transaction.contract_date.desc()).limit(500)
    ).all()
    seen, complexes = set(), []
    for r in rows:
        key = (r.complex_name, r.lawd_cd, r.property_type)
        if key in seen:
            continue
        seen.add(key)
        complexes.append({
            "complex_name": r.complex_name, "lawd_cd": r.lawd_cd,
            "property_type": r.property_type, "gu": _gu_name(r.lawd_cd),
            "dong": r.dong_name, "latest_amount": r.deal_amount,
        })
        if len(complexes) >= 8:
            break

    # --- 지역(구 + 동) ---
    regions = []
    for d in CHEONGJU_DISTRICTS:
        if q in d.name:
            regions.append({"type": "gu", "gu": d.name, "lawd_cd": d.code})
    drows = db.execute(
        select(Transaction.dong_name, Transaction.lawd_cd)
        .where(Transaction.dong_name.like(like)).distinct().limit(40)
    ).all()
    seen_d = set()
    for dong, code in drows:
        if not dong:
            continue
        k = (dong, code)
        if k in seen_d:
            continue
        seen_d.add(k)
        regions.append({"type": "dong", "gu": _gu_name(code), "dong": dong, "lawd_cd": code})
        if len(regions) >= 10:
            break

    # --- 등록 매물 ---
    lrows = db.scalars(
        select(Listing).where(
            Listing.status == "active",
            or_(Listing.title.like(like), Listing.complex_name.like(like),
                Listing.dong_name.like(like)),
        ).order_by(Listing.created_at.desc()).limit(8)
    ).all()
    listings = [{
        "id": x.id, "title": x.title, "deal_type": x.deal_type,
        "property_type": x.property_type, "gu": _gu_name(x.lawd_cd), "dong": x.dong_name,
        "price": x.price, "deposit": x.deposit, "monthly_rent": x.monthly_rent,
        "photo": (x.photos or [None])[0] if x.photos else None,
        "is_sample": x.is_sample,
    } for x in lrows]

    return {"q": q, "complexes": complexes, "regions": regions, "listings": listings}
