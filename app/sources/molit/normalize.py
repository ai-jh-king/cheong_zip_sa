"""
정규화: 유형별로 제각각인 국토부 원본 필드 → 공통 Transaction 스키마.

설계 원칙 (왜곡 없음):
  1) 필드명을 추측하지 않는다. 후보 키 목록(FIELD_CANDIDATES)으로 매핑하고,
     매칭 실패한 필드는 '지어내지 않고' None 으로 두고 경고 로그를 남긴다.
     → Swagger 확인 후 후보 키만 보강하면 즉시 정확해진다.
  2) 원본 dict 전체를 raw_payload 로 보존한다.
  3) 단독·다가구는 단지명/지번 일부만 제공되는 경우가 있어 nullable 을 허용한다.
  4) 금액은 '12,345' 같은 콤마 문자열 → 정수(만원)로 안전 변환.
"""
from __future__ import annotations
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

# 공통 의미 → 원본에서 찾아볼 후보 필드명들(우선순위 순).
# ⚠️ 실제 Swagger 응답을 보고 부족한 후보를 '추가'만 하면 됨. 임의 단정 금지.
FIELD_CANDIDATES = {
    "complex_name": ["aptNm", "offiNm", "mhouseNm", "연립다세대", "아파트", "단지명"],
    "dong_name":    ["umdNm", "법정동", "동"],
    "exclusive_area": ["excluUseAr", "전용면적", "연면적"],
    "floor":        ["floor", "층"],
    "build_year":   ["buildYear", "건축년도"],
    "deal_amount":  ["dealAmount", "거래금액"],
    "deposit":      ["deposit", "보증금액", "보증금"],
    "monthly_rent": ["monthlyRent", "월세금액", "월세"],
    # 계약일 구성요소
    "year":         ["dealYear", "년"],
    "month":        ["dealMonth", "월"],
    "day":          ["dealDay", "일"],
    # 해제(취소)/정정 — 국토부 응답이 행마다 제공(해제여부 'O', 해제사유발생일 'YY.MM.DD')
    "canceled":      ["cdealType", "해제여부"],
    "canceled_date": ["cdealDay", "해제사유발생일"],
    # 거래유형(중개거래/직거래) — 매매 응답에 제공(전월세는 보통 미제공)
    "trade_method":  ["dealingGbn", "거래유형"],
}


def _pick(row: dict, key: str):
    for cand in FIELD_CANDIDATES[key]:
        if cand in row and row[cand] not in ("", None):
            return row[cand]
    return None


def _to_int_won(value) -> int | None:
    """'12,345' / '12345' → 12345(만원). 빈값·이상값은 None."""
    if value is None:
        return None
    s = str(value).replace(",", "").strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        logger.debug("금액 파싱 실패: %r", value)
        return None


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _to_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def _build_date(row: dict) -> date | None:
    y, m, d = _to_int(_pick(row, "year")), _to_int(_pick(row, "month")), _to_int(_pick(row, "day"))
    if y and m and d:
        try:
            return date(y, m, d)
        except ValueError:
            return None
    return None


def _parse_canceled(row: dict) -> bool:
    """해제여부 'O'(대문자 오) → True. 그 외/빈값 → False."""
    v = _pick(row, "canceled")
    return str(v).strip().upper() == "O" if v is not None else False


def _parse_trade_method(row: dict) -> str | None:
    """거래유형 → 'direct'(직거래)/'agent'(중개거래)/None. 공백·하이픈은 미상."""
    v = _pick(row, "trade_method")
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("-", "—"):
        return None
    if "직거래" in s:
        return "direct"
    if "중개" in s:
        return "agent"
    return None


def _parse_cancel_date(row: dict) -> date | None:
    """해제사유발생일. 'YY.MM.DD' / 'YYYY-MM-DD' / 'YYYYMMDD' 방어적 파싱."""
    v = _pick(row, "canceled_date")
    if not v:
        return None
    s = str(v).strip().replace("-", ".").replace("/", ".")
    try:
        if "." in s:
            parts = [p for p in s.split(".") if p != ""]
            if len(parts) == 3:
                y, m, d = (int(parts[0]), int(parts[1]), int(parts[2]))
                if y < 100:
                    y += 2000
                return date(y, m, d)
        elif len(s) == 8 and s.isdigit():
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return None
    return None


def _classify_deal(deposit: int | None, monthly_rent: int | None, deal_fetch_type: str) -> str:
    """매매/전세/월세 판별. trade=매매. rent 중 월세>0=월세, 아니면 전세."""
    if deal_fetch_type == "trade":
        return "trade"
    if monthly_rent and monthly_rent > 0:
        return "wolse"
    return "jeonse"


class NormalizationReport:
    """정규화 매핑 진단 누적기(선택). normalize_row 에 넘기면 미매핑을 집계.

    넘기지 않으면 normalize_row 동작은 완전히 동일(기존 호출부 영향 없음).
    실데이터 배포 시 '어떤 핵심 필드가 몇 % 매핑 실패했는지 + 원본 키 샘플'을
    한눈에 보여줘 Swagger 후보 보강 지점을 즉시 찾게 한다.

    핵심 필드(유형별):
      - deal_amount: 매매(trade)일 때 필수
      - contract_date: 항상 필수
      - exclusive_area: 아파트/오피스텔/연립다세대 필수(단독·다가구는 연면적이라 제외)
      - complex_name: 아파트/오피스텔 필수(단독·다가구·일부 빌라는 미제공 가능 → 제외)
    """

    _AREA_TYPES = {"apartment", "officetel", "rowhouse"}
    _NAME_TYPES = {"apartment", "officetel"}

    def __init__(self):
        self.total = 0
        self.miss: dict[str, int] = {}
        self.samples: dict[str, list] = {}

    def _fail(self, field: str, row: dict):
        self.miss[field] = self.miss.get(field, 0) + 1
        bucket = self.samples.setdefault(field, [])
        if len(bucket) < 3:
            bucket.append(sorted(row.keys()))

    def observe(self, row: dict, norm: dict, deal_fetch_type: str, property_type: str):
        self.total += 1
        if deal_fetch_type == "trade" and norm.get("deal_amount") is None:
            self._fail("deal_amount", row)
        if norm.get("contract_date") is None:
            self._fail("contract_date", row)
        if property_type in self._AREA_TYPES and norm.get("exclusive_area") is None:
            self._fail("exclusive_area", row)
        if property_type in self._NAME_TYPES and not norm.get("complex_name"):
            self._fail("complex_name", row)

    def has_issues(self) -> bool:
        return bool(self.miss)

    def summary(self) -> dict:
        return {"rows": self.total, "misses": dict(self.miss),
                "miss_samples": {k: v[:3] for k, v in self.samples.items()}}


def normalize_row(
    row: dict,
    *,
    property_type: str,
    deal_fetch_type: str,
    lawd_cd: str,
    source: str,
    is_sample: bool = False,
    report: "NormalizationReport | None" = None,
) -> dict:
    """원본 1행 → Transaction 생성용 dict. 매핑 실패 필드는 None + 경고.

    report 를 넘기면(선택) 미매핑 통계를 누적한다. 넘기지 않으면 동작 동일.
    """
    deposit = _to_int_won(_pick(row, "deposit"))
    monthly_rent = _to_int_won(_pick(row, "monthly_rent"))
    deal_amount = _to_int_won(_pick(row, "deal_amount"))
    deal_type = _classify_deal(deposit, monthly_rent, deal_fetch_type)
    contract_date = _build_date(row)

    if deal_fetch_type == "trade" and deal_amount is None:
        logger.warning(
            "[%s] 매매금액 매핑 실패 — Swagger 로 필드 확인 필요. row keys=%s",
            source, list(row.keys()),
        )

    complex_name = _pick(row, "complex_name")
    area = _to_float(_pick(row, "exclusive_area"))

    norm = {
        "lawd_cd": lawd_cd,
        "property_type": property_type,
        "deal_type": deal_type,
        # 내부 공백 제거: 같은 단지를 매매/전월세·오피스텔 API가 '강서 베리굿'/'강서베리굿'처럼
        # 다르게 표기해 별개 단지로 쪼개지던 실사고(2026-07, 11개 단지) 방지. 표기 통일=무공백.
        "complex_name": re.sub(r"\s+", "", str(complex_name)) if complex_name else None,
        "dong_name": (_pick(row, "dong_name") or None),
        "exclusive_area": area,
        "floor": _to_int(_pick(row, "floor")),
        "build_year": _to_int(_pick(row, "build_year")),
        "contract_date": contract_date,
        "deal_amount": deal_amount,
        "deposit": deposit,
        "monthly_rent": monthly_rent,
        "source": "FIXTURE" if is_sample else source,
        "is_sample": is_sample,
        "raw_payload": row,
        "is_canceled": _parse_canceled(row),
        "canceled_date": _parse_cancel_date(row),
        "trade_method": _parse_trade_method(row),
    }
    norm["dedup_key"] = make_dedup_key(norm)
    norm["identity_key"] = make_identity_key(norm)
    if report is not None:
        report.observe(row, norm, deal_fetch_type, property_type)
    return norm


def make_dedup_key(n: dict) -> str:
    """같은 거래(금액 포함) 중복 적재 방지용 안정 키 — 정확히 동일한 1행 식별."""
    return "|".join(str(x) for x in [
        n["property_type"], n["deal_type"], n["lawd_cd"],
        n.get("complex_name"), n.get("exclusive_area"), n.get("floor"),
        n.get("contract_date"), n.get("deal_amount"),
        n.get("deposit"), n.get("monthly_rent"),
    ])


def make_identity_key(n: dict) -> str:
    """계약 식별 키 — '금액 제외'. 정정(금액 변경)·해제분을 같은 계약으로 매칭하기 위함.
    (단지/전용/층/계약일/동까지로 식별. 같은 조건의 별개 거래가 둘 이상이면 모호 처리.)"""
    return "|".join(str(x) for x in [
        n["property_type"], n["deal_type"], n["lawd_cd"],
        n.get("complex_name"), n.get("exclusive_area"), n.get("floor"),
        n.get("contract_date"), n.get("dong_name"),
    ])
