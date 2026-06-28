"""공동주택 기본정보(K-apt) 응답 → Complex 보강 dict 정규화.

원칙(왜곡 방지): 매핑 실패 필드는 None(빈 값 날조 금지). 필드명은 Swagger 로 확정하되,
명세 변동에 견고하도록 후보 키 매핑을 사용한다.

기본정보 Item 주요 필드(문서 기준):
  kaptCode(아파트코드) kaptName(아파트명) kaptdaCnt(세대수) kaptDongCnt(동수)
  kaptUsedate(사용승인일) codeHeatNm(난방방식) kaptTarea(연면적) kaptBcompany(시공사)
상세정보(getAphusDtlInfoV3) 주차: kaptdPcnt(지상)+kaptdPcntu(지하) 또는 총주차 관련 필드.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# 우리 필드 -> 원본 후보 키들
_FIELD_CANDIDATES = {
    "kapt_code": ["kaptCode"],
    "households": ["kaptdaCnt", "hsdCnt", "kaptDaCnt"],
    "dong_count": ["kaptDongCnt", "dongCnt"],
    "approval_date": ["kaptUsedate", "useAprDay", "useDate"],
    "heating": ["codeHeatNm", "heatNm", "codeHeat"],
    "total_area": ["kaptTarea", "kaptMarea", "tArea"],
    "builder": ["kaptBcompany", "bcompany"],
}
# 주차(상세정보에 있을 수 있음): 지상+지하 합산 후보
_PARK_TOTAL = ["kaptdPcntTot", "totPark", "kaptdParkTot"]
_PARK_GROUND = ["kaptdPcnt"]
_PARK_BASEMENT = ["kaptdPcntu"]


def _pick(item: dict, keys: list[str]):
    for k in keys:
        if k in item and str(item[k]).strip() not in ("", "None"):
            return item[k]
    return None


def _to_int(v):
    try:
        return int(float(str(v).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def _to_float(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _build_year(approval) -> int | None:
    """사용승인일(YYYYMMDD/YYYY.MM.DD/YYYY-MM-DD 등) → 연도."""
    if not approval:
        return None
    digits = "".join(ch for ch in str(approval) if ch.isdigit())
    if len(digits) >= 4:
        try:
            y = int(digits[:4])
            if 1960 <= y <= 2100:
                return y
        except ValueError:
            return None
    return None


def normalize_basis(item: dict) -> dict:
    """기본정보 Item dict → Complex 보강 dict(없는 값은 None)."""
    if not item:
        return {}
    out: dict = {}
    out["kapt_code"] = _pick(item, _FIELD_CANDIDATES["kapt_code"])
    out["households"] = _to_int(_pick(item, _FIELD_CANDIDATES["households"]))
    out["dong_count"] = _to_int(_pick(item, _FIELD_CANDIDATES["dong_count"]))
    approval = _pick(item, _FIELD_CANDIDATES["approval_date"])
    out["approval_date"] = str(approval).strip() if approval else None
    out["build_year"] = _build_year(approval)
    out["heating"] = (lambda h: str(h).strip() if h else None)(_pick(item, _FIELD_CANDIDATES["heating"]))
    out["total_area"] = _to_float(_pick(item, _FIELD_CANDIDATES["total_area"]))
    out["builder"] = (lambda b: str(b).strip() if b else None)(_pick(item, _FIELD_CANDIDATES["builder"]))

    park = _to_int(_pick(item, _PARK_TOTAL))
    if park is None:
        g, b = _to_int(_pick(item, _PARK_GROUND)), _to_int(_pick(item, _PARK_BASEMENT))
        park = (g or 0) + (b or 0) if (g is not None or b is not None) else None
    out["parking"] = park

    out["meta_source"] = "KAPT"
    # 모두 None 이면 보강 가치 없음 → 빈 dict 취급은 호출부에서 판단
    return out
