"""공공데이터(Place) 수집 공통 유틸 — tolerant 필드 매핑·좌표·청주 필터·페이지 수집.

체육/의료 등 어댑터가 공유. 학원(academy.py)은 자체 사본 유지(기검증).
"""
from __future__ import annotations
import logging

import httpx

logger = logging.getLogger(__name__)

# 청주 4개 구 → 법정동코드 앞5
GU_TO_LAWD = {"상당구": "43111", "서원구": "43112", "흥덕구": "43113", "청원구": "43114"}


def pick(row: dict, keys: list[str]):
    """여러 후보 필드명 중 첫 비어있지 않은 값."""
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return None


def to_float(v):
    try:
        f = float(v)
        return f if f != 0 else None
    except (TypeError, ValueError):
        return None


def to_int(v):
    try:
        return int(float(str(v).replace(",", "").replace("원", "").strip()))
    except (TypeError, ValueError):
        return None


def lawd_of(*texts) -> str | None:
    """주소/시군구 텍스트에서 청주 구 → 법정동코드. 청주 아니면 None."""
    blob = " ".join(str(t or "") for t in texts)
    for gu, code in GU_TO_LAWD.items():
        if gu in blob:
            return code
    return None


def is_cheongju(*texts) -> bool:
    blob = " ".join(str(t or "") for t in texts)
    return ("청주" in blob) or any(gu in blob for gu in GU_TO_LAWD)


# EPSG:5174(Bessel 중부원점TM) → WGS84. pyproj 있으면 사용, 없으면 좌표 포기(왜곡 방지).
def wgs84_from_tm5174(x, y):
    """TM(5174) → (lat, lng). 변환 불가/범위 밖이면 (None, None) — 틀린 좌표 저장 금지."""
    fx, fy = to_float(x), to_float(y)
    if fx is None or fy is None:
        return None, None
    try:
        from pyproj import Transformer  # requirements: pyproj(선택)
        t = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)
        lng, lat = t.transform(fx, fy)
        if 33.0 < lat < 39.0 and 124.0 < lng < 132.0:   # 한국 범위 sanity
            return round(lat, 6), round(lng, 6)
    except Exception as e:
        logger.warning("TM5174 변환 실패(pyproj 미설치 가능): %s", e)
    return None, None


def fetch_pages(url: str, service_key: str, *, limit_pages: int = 60, per_page: int = 1000,
                extra_params: dict | None = None) -> list[dict]:
    """odcloud 류 페이지네이션 수집(page/perPage). 실패/빈 응답이면 중단. 원본 dict 목록 반환."""
    if not service_key:
        logger.warning("%s: 서비스키 없음 → 수집 생략", url)
        return []
    rows: list[dict] = []
    try:
        with httpx.Client(timeout=20) as client:
            for page in range(1, limit_pages + 1):
                params = {"serviceKey": service_key, "page": page,
                          "perPage": per_page, "returnType": "JSON"}
                if extra_params:
                    params.update(extra_params)
                r = client.get(url, params=params)
                if r.status_code != 200:
                    logger.warning("%s: HTTP %s (page %s)", url, r.status_code, page)
                    break
                data = r.json()
                batch = data.get("data") or data.get("items") or []
                if not batch:
                    break
                rows.extend(batch)
                if len(batch) < per_page:
                    break
    except Exception as e:
        logger.warning("%s: 수집 오류 %s", url, e)
    return rows
