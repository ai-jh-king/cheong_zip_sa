"""공동주택 공시가격 보강 — 국토교통부 공식 CSV(호별) → 단지별 중앙값.

배경(정확성): 공동주택 공시가격은 깔끔한 단지단위 REST API 가 없고(호별 1,500만건 CSV·공간정보 위주),
부동산공시가격알리미/공공데이터포털에서 '공동주택가격' CSV 로 공개된다.
→ 운영자가 해당 CSV(가능하면 충북/청주로 필터)를 받아 경로를 주면, 단지×면적 '호별 가격의 중앙값'으로
   집계해 단지에 보강한다. 매칭은 단지명(정규화)+구. 매칭 실패는 보강하지 않음(null 유지·날조 금지).

⚠️ CSV 컬럼명은 배포 회차마다 다를 수 있어 후보 매핑으로 처리한다(레이아웃 확인 권장).
"""
from __future__ import annotations
import csv
import logging
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complex
from app.data.region_codes import CHEONGJU_DISTRICTS
from app.services.appmeta import set_json
from app.core.cache import bump_data_version

logger = logging.getLogger(__name__)

# 후보 컬럼(원본 헤더 변형 대응)
_COL_NAME = ["단지명", "공동주택명", "건물명", "aptNm"]
_COL_PRICE = ["공동주택가격(원)", "공동주택가격", "공시가격", "공동주택가격(원)"]
_COL_ADDR = ["법정동주소", "주소", "소재지", "시군구", "법정동명"]
_COL_AREA = ["전용면적(㎡)", "전용면적", "전용면적(M2)", "면적"]
_COL_DATE = ["공시기준일", "공시기준일자", "기준일"]

_GU_BY_KEYWORD = {d.name: d.code for d in CHEONGJU_DISTRICTS}  # '상당구'->43111 등


def _norm_name(s: str | None) -> str:
    if not s:
        return ""
    out, skip = [], False
    for ch in s:
        if ch in "([{":
            skip = True
        elif ch in ")]}":
            skip = False
        elif not skip and not ch.isspace():
            out.append(ch)
    return "".join(out)


def _pick(row: dict, keys: list[str]):
    for k in keys:
        if k in row and str(row[k]).strip() != "":
            return row[k]
    return None


def _gu_code(addr: str | None) -> str | None:
    if not addr:
        return None
    for gu, code in _GU_BY_KEYWORD.items():
        if gu in addr:  # '상당구' 포함 여부
            return code
    return None


def _to_won(v) -> int | None:
    try:
        return int(float(str(v).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def aggregate_gongsi(rows: list[dict]) -> dict:
    """호별 행 리스트 → {(단지명_norm, lawd_cd): {'price_manwon': median만원, 'basis': 기준일}}.

    청주 4개 구만 집계(다른 지역 행은 무시). 가격은 원→만원 변환 후 중앙값.
    """
    buckets: dict[tuple, list] = {}
    basis: dict[tuple, str] = {}
    for r in rows:
        gu = _gu_code(_pick(r, _COL_ADDR) or "")
        if not gu:
            continue
        name = _norm_name(_pick(r, _COL_NAME))
        won = _to_won(_pick(r, _COL_PRICE))
        if not name or won is None:
            continue
        key = (name, gu)
        buckets.setdefault(key, []).append(won)
        d = _pick(r, _COL_DATE)
        if d and key not in basis:
            basis[key] = str(d).strip()
    out = {}
    for key, vals in buckets.items():
        out[key] = {"price_manwon": round(median(vals) / 10000), "basis": basis.get(key)}
    return out


def import_from_csv(db: Session, path: str) -> dict:
    """공식 공시가격 CSV 를 읽어 단지에 보강. 파일 없으면 건너뜀."""
    import os
    if not path or not os.path.exists(path):
        return {"skipped": f"CSV 경로 없음: {path}"}
    rows = []
    # UTF-8(BOM)·CP949 모두 시도
    for enc in ("utf-8-sig", "cp949"):
        try:
            with open(path, encoding=enc, newline="") as f:
                rows = list(csv.DictReader(f))
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if not rows:
        return {"skipped": "CSV 읽기 실패 또는 빈 파일"}

    agg = aggregate_gongsi(rows)
    updated = 0
    for (name_norm, gu), info in agg.items():
        # 우리 DB 의 단지 중 정규화명이 일치하는 것 매칭
        cands = db.scalars(select(Complex).where(Complex.lawd_cd == gu)).all()
        match = next((c for c in cands if _norm_name(c.name) == name_norm), None)
        if not match:
            continue
        match.price_official = info["price_manwon"]
        match.price_basis_date = info["basis"]
        if not match.meta_source:
            match.meta_source = "GONGSI"
        updated += 1
    db.commit()
    if updated:
        bump_data_version()
    set_json(db, "last_gongsi", {"rows": len(rows), "aggregated": len(agg), "updated": updated})
    logger.info("공시가격 보강: 행 %s / 단지집계 %s / 매칭 %s", len(rows), len(agg), updated)
    return {"rows": len(rows), "aggregated": len(agg), "updated": updated}
