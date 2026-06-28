"""단지 기본정보 보강 — 실거래에 등장한 단지(아파트)를 K-apt 기본정보로 채운다.

원칙(왜곡 방지):
  - 실데이터만: K-apt 응답으로 받은 값만 저장. 매칭 실패/미설정 시 아무것도 만들지 않음(null 유지).
  - 아파트만 대상(K-apt 는 공동주택). 오피스텔/빌라/단독은 대상 아님 → null 유지.
  - 단지명 매칭은 정규화(공백/괄호 제거) 후 정확/포함 매칭. 모호하면 건너뜀.
  - 배치/스크립트로 실행(요청 핫패스 아님). 진행상황은 app_meta(last_enrich)에 기록.
"""
from __future__ import annotations
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complex, Transaction
from app.sources.kapt import client as kapt
from app.sources.kapt.normalize import normalize_basis
from app.services import appmeta
from app.core.cache import bump_data_version

logger = logging.getLogger(__name__)


class EnrichDisabled(RuntimeError):
    pass


def _norm_name(s: str | None) -> str:
    if not s:
        return ""
    out = []
    skip = False
    for ch in s:
        if ch in "([{":
            skip = True
        elif ch in ")]}":
            skip = False
        elif not skip and not ch.isspace():
            out.append(ch)
    return "".join(out)


def _get_or_create_complex(db: Session, name: str, lawd_cd: str, ptype: str) -> Complex:
    cx = db.scalar(select(Complex).where(Complex.name == name, Complex.lawd_cd == lawd_cd))
    if not cx:
        cx = Complex(name=name, lawd_cd=lawd_cd, property_type=ptype)
        db.add(cx)
        db.flush()
    return cx


def enrich_complexes(db: Session, limit: int | None = None) -> dict:
    """아파트 단지를 K-apt 기본정보로 보강. (처리/보강/미매칭 건수 반환)"""
    from app.core.config import get_settings
    s = get_settings()
    if not (s.kapt_list_url and s.kapt_info_url and s.molit_service_key):
        raise EnrichDisabled(
            "KAPT_LIST_URL/KAPT_INFO_URL 와 MOLIT_SERVICE_KEY 가 필요합니다(.env). "
            "미설정 시 보강을 건너뜁니다(날조하지 않음).")

    # 실거래에 등장한 (단지명, lawd_cd) 아파트 목록
    pairs = db.execute(
        select(Transaction.complex_name, Transaction.lawd_cd)
        .where(Transaction.property_type == "apartment",
               Transaction.complex_name.isnot(None),
               Transaction.is_sample.is_(False))
        .distinct()
    ).all()

    # 시군구별 K-apt 목록 캐시(정규화명 -> kaptCode)
    list_cache: dict[str, dict[str, str]] = {}
    processed = enriched = unmatched = 0

    for name, lawd_cd in pairs:
        if limit and processed >= limit:
            break
        processed += 1

        if lawd_cd not in list_cache:
            mapping: dict[str, str] = {}
            for it in kapt.list_complexes(lawd_cd):
                mapping[_norm_name(it["kaptName"])] = it["kaptCode"]
            list_cache[lawd_cd] = mapping

        mapping = list_cache[lawd_cd]
        key = _norm_name(name)
        code = mapping.get(key)
        if not code:  # 포함 매칭(부분일치) — 모호하면 단일 후보일 때만
            cands = [c for k, c in mapping.items() if key and (key in k or k in key)]
            code = cands[0] if len(cands) == 1 else None
        if not code:
            unmatched += 1
            continue

        item = kapt.basis_info(code)
        norm = normalize_basis(item) if item else {}
        if not norm or all(v is None for k, v in norm.items() if k != "meta_source"):
            unmatched += 1
            continue

        cx = _get_or_create_complex(db, name, lawd_cd, "apartment")
        for field in ("kapt_code", "households", "dong_count", "build_year",
                      "approval_date", "heating", "total_area", "builder", "parking"):
            val = norm.get(field)
            if val is not None:
                setattr(cx, field, val)
        cx.meta_source = "KAPT"
        cx.enriched_at = datetime.utcnow()
        enriched += 1

    db.commit()
    if enriched:
        bump_data_version()
    appmeta.set_json(db, "last_enrich", {"at": datetime.utcnow().isoformat() + "Z",
                                         "processed": processed, "enriched": enriched,
                                         "unmatched": unmatched})
    logger.info("단지 보강: 처리 %s / 보강 %s / 미매칭 %s", processed, enriched, unmatched)
    return {"processed": processed, "enriched": enriched, "unmatched": unmatched}
