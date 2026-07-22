"""
국토부 실거래가 HTTP 클라이언트.
- serviceKey 없으면 호출하지 않고 명확히 에러 (지침서: 빈 응답·에러 처리 포함).
- 레이트리밋·타임아웃·간단 재시도 적용 (공공 API 일일 한도 보호).
- 응답은 XML 이 기본 → dict 리스트로 파싱해 normalize 로 넘긴다.
- 절대 값을 지어내지 않는다. 실패 시 예외 또는 빈 리스트 + 로그.
"""
from __future__ import annotations
import time
import logging
import xml.etree.ElementTree as ET
from urllib.parse import unquote

import httpx

from app.core.config import get_settings
from app.sources.molit.endpoints import MOLIT_BASE, MOLIT_ENDPOINTS

logger = logging.getLogger(__name__)


class MolitKeyMissingError(RuntimeError):
    pass


class MolitAuthError(RuntimeError):
    """serviceKey 거부(401/403 또는 미등록). 활용신청·키 종류 점검 필요."""


def _normalize_key(raw: str) -> str:
    """인코딩/디코딩 키 혼동 방지.
    포털의 'Encoding 키'(%2B,%2F,%3D 포함)를 그대로 넣으면 httpx 가 다시 인코딩해
    이중 인코딩 → 401. 미리 한 번 unquote 해 '원본(디코딩) 키'로 통일한다.
    => 사용자가 어떤 키를 붙여넣어도 동작.
    """
    key = (raw or "").strip()
    if "%" in key:  # 이미 percent-encoded 로 보이면 한 번 풀어줌
        try:
            key = unquote(key)
        except Exception:  # noqa
            pass
    return key


class MolitClient:
    def __init__(self) -> None:
        self.s = get_settings()
        self._key = _normalize_key(self.s.molit_service_key)
        self._min_interval = 1.0 / max(self.s.molit_rate_limit_per_sec, 0.1)
        self._last_call = 0.0

    def _throttle(self) -> None:
        gap = time.monotonic() - self._last_call
        if gap < self._min_interval:
            time.sleep(self._min_interval - gap)
        self._last_call = time.monotonic()

    def fetch(
        self,
        property_type: str,
        deal_fetch_type: str,
        lawd_cd: str,
        deal_ymd: str,        # 'YYYYMM'
        num_of_rows: int = 1000,
    ) -> tuple[list[dict], str]:
        """
        단일 (유형, 거래종류, 지역, 계약년월) 조회.
        반환: (item dict 리스트, source 라벨)
        """
        if not self.s.molit_enabled:
            raise MolitKeyMissingError(
                "MOLIT_SERVICE_KEY 가 .env 에 없습니다. 실거래 API 를 호출할 수 없습니다."
            )

        meta = MOLIT_ENDPOINTS[(property_type, deal_fetch_type)]
        base = getattr(self.s, "molit_base_url", "") or MOLIT_BASE
        url = base + meta["path"]

        # 페이지네이션: 월 거래가 numOfRows(1000) 초과 시 pageNo=1 고정이면 초과분이
        # '조용히 누락'된다(왜곡 없음 위반·대도시 확장 차단). 가득 찬 페이지면 다음 페이지 계속.
        all_items: list[dict] = []
        page = 1
        MAX_PAGES = 10   # 폭주 방지(월 1만 건 상한 — 시군구 단위에선 도달 불가 수준)
        while page <= MAX_PAGES:
            params = {
                "serviceKey": self._key,
                "LAWD_CD": lawd_cd,
                "DEAL_YMD": deal_ymd,
                "numOfRows": num_of_rows,
                "pageNo": page,
            }
            items = None
            for attempt in range(3):
                try:
                    self._throttle()
                    resp = httpx.get(url, params=params, timeout=self.s.molit_request_timeout)
                    # 인증 실패는 재시도해도 동일 → 즉시 명확한 안내로 중단
                    if resp.status_code in (401, 403):
                        raise MolitAuthError(self._auth_help(resp.status_code, meta["source"]))
                    resp.raise_for_status()
                    items = self._parse_xml_items(resp.text, source=meta["source"])
                    break
                except MolitAuthError:
                    raise
                except (httpx.HTTPError, ET.ParseError) as e:
                    wait = 1.5 * (attempt + 1)
                    logger.warning(
                        "MOLIT 호출 실패(%s/%s) %s %s %s p%s: %s — %.1fs 후 재시도",
                        attempt + 1, 3, property_type, lawd_cd, deal_ymd, page, e, wait,
                    )
                    time.sleep(wait)
            if items is None:                      # 이 페이지 최종 실패
                if page == 1:
                    logger.error("MOLIT 호출 최종 실패: %s %s %s", property_type, lawd_cd, deal_ymd)
                    return [], meta["source"]
                logger.warning("MOLIT p%s 실패 — 이전 페이지까지 %d건 반환", page, len(all_items))
                break
            all_items.extend(items)
            if len(items) < num_of_rows:           # 마지막 페이지
                break
            page += 1
        return all_items, meta["source"]

    @staticmethod
    def _auth_help(code: int, source: str) -> str:
        return (
            f"[{source}] serviceKey 인증 거부(HTTP {code}). 다음을 확인하세요:\n"
            f"  1) data.go.kr 에서 이 데이터셋의 '활용신청'을 했고 승인됐는지 "
            f"(API 마다 따로 신청해야 함).\n"
            f"  2) .env 의 MOLIT_SERVICE_KEY 가 'Decoding(디코딩) 키'인지 "
            f"(Encoding 키를 넣으면 이중 인코딩되어 거부됨).\n"
            f"  3) 승인 직후면 동기화에 수십 분~수시간 걸릴 수 있음.\n"
            f"  4) 키 앞뒤 공백·줄바꿈이 없는지."
        )

    @staticmethod
    def _parse_xml_items(xml_text: str, source: str = "") -> list[dict]:
        """공공데이터포털 표준 XML(<items><item>...) → dict 리스트.
        필드명은 응답 원본을 그대로 보존(왜곡 방지). 의미 매핑은 normalize 단계에서."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            # 인증 실패 시 JSON/HTML 본문이 오는 경우가 있어 키워드로 진단
            low = (xml_text or "").lower()
            if "service key" in low or "not registered" in low or "unregistered" in low:
                raise MolitAuthError(
                    f"[{source}] serviceKey 미등록 응답. 활용신청 여부와 디코딩 키 사용을 확인하세요."
                )
            raise

        # 에러 응답(인증 실패 등) 감지
        header = root.find(".//resultCode")
        if header is not None and header.text not in ("00", "000", None):
            code = header.text
            msg = root.findtext(".//resultMsg") or "알 수 없는 오류"
            if code in ("30", "31") or "SERVICE_KEY" in (msg or "").upper():
                raise MolitAuthError(
                    f"[{source}] resultCode={code} ({msg}) — serviceKey 문제. "
                    f"활용신청 승인 여부 + 디코딩 키 사용을 확인하세요."
                )
            raise httpx.HTTPError(f"MOLIT 응답 오류 resultCode={code} ({msg})")

        items: list[dict] = []
        for item in root.findall(".//item"):
            row = {child.tag.strip(): (child.text or "").strip() for child in item}
            items.append(row)
        return items
