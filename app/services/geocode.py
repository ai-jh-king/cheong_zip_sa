"""
지오코딩: 단지명/법정동 → 좌표(lat,lng). 지도 표시용.

제공자 선택(GEOCODE_USE_NAVER 토글):
  · 기본(false): 카카오 로컬 단독 사용.
      - 단지명: search/keyword.json, 법정동: search/address.json. 헤더: Authorization: KakaoAK <REST키>.
      - response: documents[0].x(경도)/.y(위도).
  · true: 네이버 클라우드 Geocoding 우선 + 카카오 폴백.
      - endpoint: https://maps.apigw.ntruss.com/map-geocode/v2/geocode (신 Maps 게이트웨이)
        ⚠️ 현재 코드 상수 NAVER_GEOCODE 는 구 호스트(naveropenapi.apigw.ntruss.com)라 401 → 사용 시 신 호스트로 교체 필요.
      - headers: X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY, response: addresses[0].x/.y.

원칙(왜곡 없음):
  - '실제' 좌표만 저장. 못 찾으면 None → 지도에 표시하지 않는다.
  - 단지명 우선 → 실패 시 '시군구+법정동'(동 대략 위치, precision='dong').
  - 결과는 Complex 테이블에 캐싱(중복 호출/쿼터 절약).

참고: 인근 POI(반경 카테고리 검색)는 네이버에 동등 API가 없어 services/poi.py 는 카카오 사용.
"""
from __future__ import annotations
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.cache import bump_data_version, stat_cached
from app.data.region_codes import DISTRICT_BY_CODE
from app.models import Complex, Transaction

logger = logging.getLogger(__name__)
NAVER_GEOCODE = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
KAKAO_KEYWORD = "https://dapi.kakao.com/v2/local/search/keyword.json"
KAKAO_ADDRESS = "https://dapi.kakao.com/v2/local/search/address.json"


class GeocodeKeyMissing(RuntimeError):
    pass


def _sigungu(lawd_cd: str) -> str:
    d = DISTRICT_BY_CODE.get(lawd_cd)
    return f"청주시 {d.name}" if d else "청주시"


# ---------- 네이버(우선) ----------
def _naver_query(cid: str, csec: str, query: str) -> tuple | None:
    headers = {"X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": csec}
    try:
        url = get_settings().naver_geocode_url or NAVER_GEOCODE
        r = httpx.get(url, headers=headers, params={"query": query}, timeout=10)
        if r.status_code != 200:
            logger.debug("naver geocode %s: %s", r.status_code, r.text[:120])
            return None
        addrs = r.json().get("addresses") or []
        if addrs:
            return float(addrs[0]["y"]), float(addrs[0]["x"])
    except (httpx.HTTPError, KeyError, ValueError) as e:
        logger.debug("naver geocode 실패 %s: %s", query, e)
    return None


# ---------- 카카오(폴백) ----------
def _kakao_query(key: str, url: str, query: str) -> tuple | None:
    try:
        r = httpx.get(url, headers={"Authorization": f"KakaoAK {key}"},
                      params={"query": query}, timeout=10)
        if r.status_code == 200:
            docs = r.json().get("documents", [])
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"])
    except (httpx.HTTPError, KeyError, ValueError) as e:
        logger.debug("kakao geocode 실패 %s: %s", query, e)
    return None


def geocode_one(s, name: str | None, lawd_cd: str, dong: str | None) -> tuple | None:
    """(lat, lng, precision) 또는 None. precision: complex | dong."""
    sigungu = _sigungu(lawd_cd)
    # 지오코딩 제공자: 기본은 카카오 단독. 네이버는 GEOCODE_USE_NAVER=true 일 때만(키도 있어야).
    # (네이버 Maps 가 신 게이트웨이 maps.apigw.ntruss.com 로 이전되어 구 호스트는 401 → 기본 비활성)
    use_naver = bool(s.geocode_use_naver and s.naver_map_client_id and s.naver_map_client_secret)
    use_kakao = bool(s.kakao_rest_api_key)

    # 1) 단지명(정확)
    if name:
        if use_naver:
            hit = _naver_query(s.naver_map_client_id, s.naver_map_client_secret,
                               f"충청북도 {sigungu} {name}")
            if hit:
                return hit[0], hit[1], "complex"
        if use_kakao:
            hit = _kakao_query(s.kakao_rest_api_key, s.kakao_keyword_url or KAKAO_KEYWORD, f"충북 {sigungu} {name}")
            if hit:
                return hit[0], hit[1], "complex"

    # 2) 법정동(대략)
    if dong:
        if use_naver:
            hit = _naver_query(s.naver_map_client_id, s.naver_map_client_secret,
                               f"충청북도 {sigungu} {dong}")
            if hit:
                return hit[0], hit[1], "dong"
        if use_kakao:
            hit = _kakao_query(s.kakao_rest_api_key, s.kakao_address_url or KAKAO_ADDRESS, f"충청북도 {sigungu} {dong}")
            if hit:
                return hit[0], hit[1], "dong"
    return None


def _get_or_create_complex(db: Session, name: str, lawd_cd: str, ptype: str) -> Complex:
    cx = db.scalar(select(Complex).where(
        Complex.name == name, Complex.lawd_cd == lawd_cd))
    if not cx:
        cx = Complex(name=name, lawd_cd=lawd_cd, property_type=ptype)
        db.add(cx)
        db.flush()
    return cx


def run_geocode(db: Session, limit: int | None = None) -> dict:
    """거래에 등장한 단지들을 지오코딩해 Complex.lat/lng 에 캐싱."""
    s = get_settings()
    naver_on = bool(s.geocode_use_naver and s.naver_map_client_id and s.naver_map_client_secret)
    if not naver_on and not s.kakao_rest_api_key:
        raise GeocodeKeyMissing(
            "카카오(kakao_rest_api_key) 키가 필요합니다. "
            "(네이버 지오코딩을 쓰려면 GEOCODE_USE_NAVER=true + 네이버 키)")

    pairs = db.execute(
        select(Transaction.complex_name, Transaction.lawd_cd,
               Transaction.dong_name, Transaction.property_type)
        .where(Transaction.complex_name.isnot(None)).distinct()
    ).all()

    done, skipped, failed = 0, 0, 0
    for i, (name, lawd, dong, ptype) in enumerate(pairs):
        if limit and i >= limit:
            break
        cx = _get_or_create_complex(db, name, lawd, ptype or "apartment")
        if cx.lat is not None and cx.lng is not None:
            skipped += 1
            continue
        res = geocode_one(s, name, lawd, dong)
        if res:
            cx.lat, cx.lng = res[0], res[1]
            done += 1
        else:
            failed += 1
    db.commit()
    if done:
        bump_data_version()  # 좌표 변경 → 지도(heatmap) 캐시 무효화
    logger.info("지오코딩: 신규 %s · 기존 %s · 실패 %s", done, skipped, failed)
    return {"geocoded": done, "cached": skipped, "failed": failed}


def run_geocode_places(db: Session, limit: int | None = None) -> dict:
    """시설(Place) 중 좌표 없는 것을 지오코딩해 Place.lat/lng 채움.
    NEIS 학원 등 좌표 미제공 소스 대응. 도로명주소 우선 → 명칭+동 폴백.
    좌표를 못 찾으면 None 유지(틀린 좌표 저장 금지 — 왜곡 방지)."""
    from app.models import Place
    s = get_settings()
    use_naver = bool(s.geocode_use_naver and s.naver_map_client_id and s.naver_map_client_secret)
    use_kakao = bool(s.kakao_rest_api_key)
    if not (use_naver or use_kakao):
        raise GeocodeKeyMissing(
            "지오코딩 키가 필요합니다. KAKAO_REST_API_KEY(권장) "
            "또는 GEOCODE_USE_NAVER=true + 네이버 키.")
    q = select(Place).where(Place.lat.is_(None))
    if limit:
        q = q.limit(limit)
    rows = db.scalars(q).all()
    done = failed = 0
    for i, p in enumerate(rows):
        hit = None
        addr = getattr(p, "road_address", None)
        if addr:   # 도로명주소가 가장 정확
            if use_kakao:
                hit = (_kakao_query(s.kakao_rest_api_key, s.kakao_address_url or KAKAO_ADDRESS, addr)
                       or _kakao_query(s.kakao_rest_api_key, s.kakao_keyword_url or KAKAO_KEYWORD, addr))
            if not hit and use_naver:
                hit = _naver_query(s.naver_map_client_id, s.naver_map_client_secret, addr)
        if not hit:   # 명칭+시군구, 그다음 동 폴백(geocode_one 재사용)
            res = geocode_one(s, p.name, p.lawd_cd or "43111", getattr(p, "dong_name", None))
            if res:
                hit = (res[0], res[1])
        if hit:
            p.lat, p.lng = hit[0], hit[1]
            done += 1
        else:
            failed += 1
        if done and done % 50 == 0:
            db.commit()
    db.commit()
    if done:
        bump_data_version()  # 시설 좌표 변경 → 지도 POI 캐시 무효화
    logger.info("시설 지오코딩: 성공 %s · 실패 %s (대상 %s)", done, failed, len(rows))
    return {"geocoded": done, "failed": failed, "total": len(rows)}


@stat_cached()
def coords_map(db: Session) -> dict:
    """{(단지명, lawd_cd): (lat, lng)} — 좌표 있는 것만. 매 요청 풀스캔 방지 위해 캐시(지오코딩 시 무효화)."""
    return {(c.name, c.lawd_cd): (c.lat, c.lng)
            for c in db.scalars(select(Complex).where(Complex.lat.isnot(None)))}
