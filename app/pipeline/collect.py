"""
수집 파이프라인 (M1 핵심).
지침서 6·8장: 외부 API 를 매 요청마다 직접 호출 금지 → 자체 DB 에 캐싱·증분 수집.

흐름:
  지역(4개 구) × 유형(4) × 거래종류(trade/rent) × 계약년월(N개월)
   → MOLIT 호출 → normalize → dedup 후 DB upsert.

오프라인/키 없음일 때는 fixtures 로 동일 경로를 태워 파이프라인을 검증할 수 있다
(이때 들어가는 데이터는 is_sample=True, source='FIXTURE' 로 명확히 표식 → 절대 실데이터로 오인 안 됨).
"""
from __future__ import annotations
import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.cache import bump_data_version
from app.services import appmeta
from datetime import datetime as _dt
from app.data.region_codes import CHEONGJU_DISTRICTS
from app.models import Region, Transaction
from app.sources.molit.client import MolitClient, MolitKeyMissingError
from app.sources.molit.endpoints import PROPERTY_TYPES, DEAL_FETCH_TYPES
from app.sources.molit.normalize import normalize_row, make_identity_key, NormalizationReport

logger = logging.getLogger(__name__)


def _recent_months(n: int) -> list[str]:
    out, cur = [], date.today().replace(day=1)
    for _ in range(n):
        out.append(cur.strftime("%Y%m"))
        cur = _minus_month(cur)
    return out


def _minus_month(d: date) -> date:
    y, m = (d.year, d.month - 1)
    if m == 0:
        y, m = y - 1, 12
    return date(y, m, 1)


def ensure_regions(db: Session) -> None:
    """region_codes 표를 DB Region 테이블에 반영(없으면 생성)."""
    for dgu in CHEONGJU_DISTRICTS:
        if not db.get(Region, dgu.code):
            db.add(Region(lawd_cd=dgu.code, sido="충청북도",
                          sigungu=f"청주시 {dgu.name}"))
    db.commit()


def backfill_identity_keys(db: Session) -> int:
    """기존 행 중 identity_key 가 비어 있으면 채운다(정정/해제 매칭 활성화)."""
    rows = db.scalars(select(Transaction).where(Transaction.identity_key.is_(None))).all()
    if not rows:
        return 0
    for t in rows:
        t.identity_key = make_identity_key({
            "property_type": t.property_type, "deal_type": t.deal_type, "lawd_cd": t.lawd_cd,
            "complex_name": t.complex_name, "exclusive_area": t.exclusive_area,
            "floor": t.floor, "contract_date": t.contract_date, "dong_name": t.dong_name,
        })
        if t.is_canceled is None:
            t.is_canceled = False
    db.commit()
    logger.info("identity_key 백필: %s 건", len(rows))
    return len(rows)


def upsert_transactions(db: Session, rows: list[dict]) -> dict:
    """증분 적재 + 정정/해제 반영. 반환={inserted, corrected, canceled}.

    - 신규: identity_key 로 활성 거래가 없으면 INSERT.
    - 정정: 같은 identity_key 활성 거래가 1건 있고 금액이 다르면 그 행을 '갱신'(중복 생성 금지).
    - 해제: 해제여부 'O' 행이면 같은 identity_key 활성 거래를 is_canceled=True 로 표시(집계 제외).
    - 완전 동일(dedup_key 일치)한 행은 skip(멱등).
    """
    if not rows:
        return {"inserted": 0, "corrected": 0, "canceled": 0}
    now = datetime.utcnow()
    dedups = [r["dedup_key"] for r in rows]
    idents = [r.get("identity_key") for r in rows if r.get("identity_key")]

    existing_dedups = set(
        db.scalars(select(Transaction.dedup_key).where(Transaction.dedup_key.in_(dedups))).all()
    )
    id_map: dict[str, list] = {}
    if idents:
        for t in db.scalars(select(Transaction).where(Transaction.identity_key.in_(idents))).all():
            id_map.setdefault(t.identity_key, []).append(t)

    inserted = corrected = canceled = 0
    for r in rows:
        ik = r.get("identity_key")
        active = [m for m in id_map.get(ik, []) if not m.is_canceled]

        if r.get("is_canceled"):
            if active:
                for m in active:
                    m.is_canceled = True
                    m.canceled_date = r.get("canceled_date") or m.canceled_date
                    canceled += 1
            elif r["dedup_key"] not in existing_dedups:
                obj = Transaction(**r)
                db.add(obj)
                existing_dedups.add(r["dedup_key"])
                id_map.setdefault(ik, []).append(obj)
            continue

        if r["dedup_key"] in existing_dedups:
            continue  # 완전히 동일한 행 존재 → skip

        if len(active) == 1:
            m = active[0]
            if (m.deal_amount, m.deposit, m.monthly_rent) != \
               (r.get("deal_amount"), r.get("deposit"), r.get("monthly_rent")):
                # 정정 — 기존 행 금액 갱신(중복 생성 금지)
                m.deal_amount = r.get("deal_amount")
                m.deposit = r.get("deposit")
                m.monthly_rent = r.get("monthly_rent")
                m.dedup_key = r["dedup_key"]
                m.corrected_at = now
                m.trade_method = r.get("trade_method")
                m.raw_payload = r.get("raw_payload")
                existing_dedups.add(r["dedup_key"])
                corrected += 1
            # 금액 동일 → 사실상 같은 거래, skip
        else:
            # 활성 0건 → 신규 / 2건 이상(모호) → 신규로 적재(기존 보존)
            obj = Transaction(**r)
            db.add(obj)
            existing_dedups.add(r["dedup_key"])
            id_map.setdefault(ik, []).append(obj)
            inserted += 1

    db.commit()
    if inserted or corrected or canceled:
        bump_data_version()  # 신규/정정/해제 → 집계 캐시 무효화(신선도)
        if corrected or canceled:
            logger.info("정정 %s · 해제 %s 반영", corrected, canceled)
    return {"inserted": inserted, "corrected": corrected, "canceled": canceled}


def collect_live(db: Session, months_back: int | None = None) -> dict:
    """실제 국토부 API 로 수집. 키 없으면 명확히 실패."""
    s = get_settings()
    months_back = months_back or s.collect_months_back
    client = MolitClient()
    if not s.molit_enabled:
        raise MolitKeyMissingError("MOLIT_SERVICE_KEY 미설정 — collect_live 불가. collect_from_fixtures 사용.")

    ensure_regions(db)
    backfill_identity_keys(db)
    months = _recent_months(months_back)
    total_new, total_seen, total_corrected, total_canceled = 0, 0, 0, 0
    report = NormalizationReport()

    for dgu in CHEONGJU_DISTRICTS:
        for ptype in PROPERTY_TYPES:
            for dft in DEAL_FETCH_TYPES:
                for ymd in months:
                    items, source = client.fetch(ptype, dft, dgu.code, ymd)
                    norm = [
                        normalize_row(it, property_type=ptype, deal_fetch_type=dft,
                                      lawd_cd=dgu.code, source=source, report=report)
                        for it in items
                    ]
                    total_seen += len(norm)
                    res = upsert_transactions(db, norm)
                    total_new += res["inserted"]
                    total_corrected += res["corrected"]
                    total_canceled += res["canceled"]
    logger.info("수집 완료: 신규 %s / 조회 %s / 정정 %s / 해제 %s",
                total_new, total_seen, total_corrected, total_canceled)
    mapping = report.summary()
    if report.has_issues():
        logger.warning("정규화 매핑 경고: %s행 중 미매핑=%s — molit/normalize.py FIELD_CANDIDATES 보강 필요(원본 키 샘플은 수집 결과 stats 참조)",
                       mapping["rows"], mapping["misses"])
    if total_new:
        bump_data_version()  # 집계 캐시 무효화(신선도)
        try:
            from app.services.notify_transactions import notify_new_transactions
            notify_new_transactions(db)  # 관심 단지/지역 신규 실거래 알림
        except Exception:
            logger.exception("실거래 알림 생성 실패(수집은 정상)")
    appmeta.set_json(db, "last_collect", {"at": _dt.utcnow().isoformat() + "Z",
                                          "mode": "live", "new": total_new, "seen": total_seen,
                                          "corrected": total_corrected, "canceled": total_canceled,
                                          "mapping_misses": mapping["misses"]})
    return {"new": total_new, "seen": total_seen, "mode": "live",
            "corrected": total_corrected, "canceled": total_canceled, "mapping": mapping}


def collect_from_fixtures(db: Session) -> dict:
    """오프라인/키 없음 검증용. fixtures 의 모의데이터를 동일 정규화 경로로 적재."""
    from app.fixtures.sample_transactions import RAW_FIXTURES
    ensure_regions(db)
    backfill_identity_keys(db)
    total_new = 0
    for fx in RAW_FIXTURES:
        norm = normalize_row(
            fx["row"], property_type=fx["property_type"],
            deal_fetch_type=fx["deal_fetch_type"], lawd_cd=fx["lawd_cd"],
            source=fx["source"], is_sample=True,
        )
        total_new += upsert_transactions(db, [norm])["inserted"]
    logger.info("[FIXTURE] 모의데이터 적재: 신규 %s", total_new)
    if total_new:
        bump_data_version()
    appmeta.set_json(db, "last_collect", {"at": _dt.utcnow().isoformat() + "Z",
                                          "mode": "fixture", "new": total_new, "seen": total_new})
    return {"new": total_new, "mode": "fixture", "warning": "is_sample=True (실데이터 아님)"}
