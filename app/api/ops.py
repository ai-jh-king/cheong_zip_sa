"""관측성 — 데이터 신선도/커버리지 공개 엔드포인트.

운영자/모니터링과 UI '데이터 기준' 배너가 함께 쓰는 집계 정보(개인정보 없음).
무거운 풀스캔을 피하려 SQL 집계(count/max/group by)만 사용한다.
"""
from __future__ import annotations
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Transaction, Complex
from app.data.region_codes import CHEONGJU_DISTRICTS
from app.services import appmeta
from app.core.cache import get_data_version

router = APIRouter(tags=["ops"])

STALE_HOURS = 36  # 마지막 수집이 이보다 오래되면 stale 로 표시(일 1회 수집 가정)


def _age_hours(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 1)
    except (TypeError, ValueError):
        return None


@router.get("/status/data")
def data_status(db: Session = Depends(get_db)):
    # 실데이터(모의·해제 제외) 기준 집계
    base = select(Transaction).where(Transaction.is_sample.is_(False),
                                     Transaction.is_canceled.isnot(True))
    total_tx = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    data_as_of = db.scalar(
        select(func.max(Transaction.contract_date)).where(
            Transaction.is_sample.is_(False), Transaction.is_canceled.isnot(True)))

    # 구별 커버리지: 건수 + 최신 계약일
    rows = db.execute(
        select(Transaction.lawd_cd, func.count(), func.max(Transaction.contract_date))
        .where(Transaction.is_sample.is_(False), Transaction.is_canceled.isnot(True))
        .group_by(Transaction.lawd_cd)
    ).all()
    by_code = {r[0]: (r[1], r[2]) for r in rows}
    per_gu = []
    for d in CHEONGJU_DISTRICTS:
        cnt, latest = by_code.get(d.code, (0, None))
        per_gu.append({"lawd_cd": d.code, "name": d.name, "count": int(cnt),
                       "latest": latest.isoformat() if latest else None})

    # 지오코딩 커버리지
    distinct_complexes = db.scalar(
        select(func.count()).select_from(
            select(Transaction.complex_name, Transaction.lawd_cd)
            .where(Transaction.complex_name.isnot(None)).distinct().subquery())) or 0
    geocoded = db.scalar(select(func.count()).select_from(Complex).where(Complex.lat.isnot(None))) or 0
    geo_pct = round(geocoded / distinct_complexes * 100, 1) if distinct_complexes else None

    last_collect = appmeta.get_json(db, "last_collect")
    collect_age = _age_hours(last_collect.get("at")) if last_collect else None
    stale = (collect_age is None) or (collect_age > STALE_HOURS)

    return {
        "data_as_of": data_as_of.isoformat() if data_as_of else None,   # 최신 계약일
        "total_transactions": int(total_tx),
        "per_gu": per_gu,
        "geocode": {"distinct_complexes": distinct_complexes, "geocoded": geocoded,
                    "coverage_pct": geo_pct},
        "last_collect": last_collect,                                   # {at,mode,new,seen}
        "last_collect_age_hours": collect_age,
        "stale": stale,
        "data_version": get_data_version(),
    }
