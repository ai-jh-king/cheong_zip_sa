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


def geocode_one(s, name: str | None, lawd_cd: str, dong: str | None,
                strict_dong: bool = False) -> tuple | None:
    """(lat, lng, precision) 또는 None. precision: complex | dong.

    strict_dong: 같은 구에 동명(同名) 단지가 여러 동에 있을 때 True — 동 없는 폴백 질의가
    다른 동의 단지를 잡아 좌표가 섞이는 것을 금지(왜곡 없음). 법정동 폴백(2)은 동이
    맞는 대략 좌표라 허용."""
    sigungu = _sigungu(lawd_cd)
    # 지오코딩 제공자: 기본은 카카오 단독. 네이버는 GEOCODE_USE_NAVER=true 일 때만(키도 있어야).
    # (네이버 Maps 가 신 게이트웨이 maps.apigw.ntruss.com 로 이전되어 구 호스트는 401 → 기본 비활성)
    use_naver = bool(s.geocode_use_naver and s.naver_map_client_id and s.naver_map_client_secret)
    use_kakao = bool(s.kakao_rest_api_key)

    # 1) 단지명(정확) — 동(dong)을 질의에 포함해 같은 구 동명(同名) 단지를 구분(v1.224).
    #    동 포함 질의 실패 시 동 없이 재시도(신도시 명칭 개편 등으로 동+이름 검색이 안 잡히는 경우).
    if name:
        queries = ([f"{sigungu} {dong} {name}"] if dong else [])
        if not (strict_dong and dong):
            queries.append(f"{sigungu} {name}")
        for q in queries:
            if use_naver:
                hit = _naver_query(s.naver_map_client_id, s.naver_map_client_secret, f"충청북도 {q}")
                if hit:
                    return hit[0], hit[1], "complex"
            if use_kakao:
                hit = _kakao_query(s.kakao_rest_api_key, s.kakao_keyword_url or KAKAO_KEYWORD, f"충북 {q}")
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


_GU_GEO = None   # 구 경계 GeoJSON(런타임 캐시). False=파일 없음(검증 생략)


def _load_gu_geo():
    global _GU_GEO
    if _GU_GEO is not None:
        return _GU_GEO
    import json
    from pathlib import Path
    base = Path(__file__).resolve().parents[2]
    for rel in ("frontend/public/geo/cheongju_gu.json", "frontend/dist/geo/cheongju_gu.json"):
        p = base / rel
        if p.exists():
            try:
                _GU_GEO = json.loads(p.read_text(encoding="utf-8"))
                return _GU_GEO
            except (OSError, ValueError):
                pass
    _GU_GEO = False
    return _GU_GEO


def _in_own_gu(lawd_cd: str, lat: float, lng: float) -> bool | None:
    """좌표가 자기 구(區) 경계 폴리곤 안에 있는지. 경계 데이터 없으면 None(검증 생략 — 왜곡 없음).

    동명(同名) 시설을 다른 구·시에서 잡은 오좌표를 걸러낸다(실사고: 시내 단지가 오송 좌표 등).
    """
    geo = _load_gu_geo()
    if not geo:
        return None

    def _inside(ring, x, y):   # 레이 캐스팅(외곽 링 기준, 의존성 없음)
        n = len(ring); j = n - 1; c = False
        for i in range(n):
            xi, yi = ring[i]; xj, yj = ring[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                c = not c
            j = i
        return c

    for f in geo.get("features", []):
        if f.get("properties", {}).get("code") != str(lawd_cd):
            continue
        g = f.get("geometry", {})
        polys = [g["coordinates"]] if g.get("type") == "Polygon" else g.get("coordinates", [])
        return any(_inside(p[0], lng, lat) for p in polys)
    return None


def _km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    from math import radians, cos, sqrt
    x = radians(lng2 - lng1) * 6371 * cos(radians(lat1))
    y = radians(lat2 - lat1) * 6371
    return sqrt(x * x + y * y)


def _dong_ref(s, lawd_cd: str, dong: str, cache_d: dict) -> tuple | None:
    """법정동 기준 좌표(주소 지오코딩, 런 중 캐시). 못 찾으면 None → 검증 생략(왜곡 없음)."""
    key = (lawd_cd, dong)
    if key not in cache_d:
        sigungu = _sigungu(lawd_cd)
        hit = None
        if s.geocode_use_naver and s.naver_map_client_id and s.naver_map_client_secret:
            hit = _naver_query(s.naver_map_client_id, s.naver_map_client_secret,
                               f"충청북도 {sigungu} {dong}")
        if not hit and s.kakao_rest_api_key:
            hit = _kakao_query(s.kakao_rest_api_key, s.kakao_address_url or KAKAO_ADDRESS,
                               f"충청북도 {sigungu} {dong}")
        cache_d[key] = hit
    return cache_d[key]


def _dong_threshold_km(s, dong: str) -> float:
    """단지 좌표가 소속 동 기준점에서 이보다 멀면 오탐(다른 지역 동명 시설을 잡은 것)으로 본다.
    읍·면(…리)은 행정구역이 넓어 완화. 값은 설정으로 조정(하드코딩 금지 원칙)."""
    rural = ("읍" in dong) or ("면" in dong) or dong.endswith("리")
    return s.geocode_validate_km_rural if rural else s.geocode_validate_km


def _payload_addresses(d: dict, sigungu: str, dong: str | None) -> tuple[str | None, str | None]:
    """실거래 raw_payload 의 공부(公簿) 주소 → (도로명주소, 지번주소) 질의 문자열.

    키워드 검색(단지명)은 동명 학원·상가를 잡는 오탐이 있어(실사고: 학교 위 가격핀),
    거래 신고에 적힌 주소를 1순위로 쓴다. 필드 없으면 None(추측 금지)."""
    road = jib = None
    rn = str(d.get("roadNm") or "").strip()
    if rn:
        try:
            bon = int(str(d.get("roadNmBonbun") or "0") or 0)
            bu = int(str(d.get("roadNmBubun") or "0") or 0)
        except ValueError:
            bon = bu = 0
        if bon:
            road = f"충청북도 {sigungu} {rn} {bon}" + (f"-{bu}" if bu else "")
    j = str(d.get("jibun") or "").strip()
    if j and dong:
        jib = f"충청북도 {sigungu} {dong} {j}"
    return road, jib


def _tx_address(db: Session, name: str, lawd_cd: str, dong: str | None) -> tuple[str | None, str | None]:
    """이 단지(이름·구·동)의 최근 거래 raw_payload 에서 주소 질의 후보 추출."""
    q = (select(Transaction.raw_payload)
         .where(Transaction.complex_name == name, Transaction.lawd_cd == lawd_cd,
                Transaction.raw_payload.isnot(None))
         .order_by(Transaction.contract_date.desc()).limit(1))
    if dong is not None:
        q = q.where(Transaction.dong_name == dong)
    row = db.execute(q).scalar()
    if not row:
        return None, None
    if isinstance(row, str):
        import json
        try:
            row = json.loads(row)
        except ValueError:
            return None, None
    if not isinstance(row, dict):
        return None, None
    return _payload_addresses(row, _sigungu(lawd_cd), dong)


def _get_or_create_complex(db: Session, name: str, lawd_cd: str, ptype: str,
                           dong: str | None = None, claim_legacy: bool = False) -> Complex:
    """동(dong) 단위 단지 행(동명 단지 분리 — v1.224).

    claim_legacy: 이 (name, lawd)의 동이 거래상 유일할 때만 True — 레거시 행(dong=None)을
    그 동으로 확정(0024 백필 누락분 안전망). 복수 동(모호)이면 레거시 좌표가 어느 동
    것인지 알 수 없으므로 절대 재사용하지 않고 새 행을 만든다(좌표 오배정=왜곡 방지)."""
    cx = db.scalar(select(Complex).where(
        Complex.name == name, Complex.lawd_cd == lawd_cd, Complex.dong == dong))
    if cx:
        return cx
    if dong is not None and claim_legacy:
        legacy = db.scalars(select(Complex).where(
            Complex.name == name, Complex.lawd_cd == lawd_cd)).all()
        if len(legacy) == 1 and legacy[0].dong is None:
            legacy[0].dong = dong
            return legacy[0]
    cx = Complex(name=name, lawd_cd=lawd_cd, property_type=ptype, dong=dong)
    db.add(cx)
    db.flush()
    return cx


def run_geocode(db: Session, limit: int | None = None, revalidate: bool = False,
                refresh: bool = False) -> dict:
    """거래에 등장한 단지들을 (이름·구·동) 단위로 지오코딩해 Complex.lat/lng 에 캐싱.

    좌표 결정 우선순위(v1.237): ①거래 신고의 도로명주소 ②지번주소(주소 지오코딩 —
    공부 주소라 동명 시설 오탐 없음) ③단지명 키워드(동 포함) ④법정동 중심 폴백.
    검증: 동 기준점 임계거리 + 구 경계 폴리곤(밖이면 저장 거부).
    revalidate=True: 저장된 좌표를 재검사해 오탐만 지우고 재지오코딩(야간 자가치유).
    refresh=True: 동 단위 단지 좌표를 전부 지우고 주소 기반으로 전면 재산출(1회성 교정).
    """
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
    # 같은 (이름, 구)가 몇 개 동에 걸치나 — 복수 동이면 strict(동 없는 폴백 질의 금지)
    dong_counts: dict[tuple, set] = {}
    for name, lawd, dong, _pt in pairs:
        dong_counts.setdefault((name, lawd), set()).add(dong)

    dong_refs: dict[tuple, tuple | None] = {}   # (lawd, dong) → 기준좌표(런 중 캐시)
    cleared = 0
    if refresh:
        for cx in db.scalars(select(Complex).where(
                Complex.lat.isnot(None), Complex.dong.isnot(None))):
            cx.lat = cx.lng = None
            cleared += 1
    elif revalidate:
        for cx in db.scalars(select(Complex).where(
                Complex.lat.isnot(None), Complex.dong.isnot(None))):
            # ①구 경계 밖(다른 구·시 동명 시설 오탐) ②동 기준점에서 임계 초과 → 좌표 폐기 후 재지오코딩
            if _in_own_gu(cx.lawd_cd, cx.lat, cx.lng) is False:
                cx.lat = cx.lng = None
                cleared += 1
                continue
            ref = _dong_ref(s, cx.lawd_cd, cx.dong, dong_refs)
            if ref and _km(cx.lat, cx.lng, ref[0], ref[1]) > _dong_threshold_km(s, cx.dong):
                cx.lat = cx.lng = None   # 오탐 → 아래 루프에서 재지오코딩
                cleared += 1

    done, skipped, failed, demoted = 0, 0, 0, 0
    for i, (name, lawd, dong, ptype) in enumerate(pairs):
        if limit and i >= limit:
            break
        strict = len(dong_counts.get((name, lawd), set())) > 1
        cx = _get_or_create_complex(db, name, lawd, ptype or "apartment", dong,
                                    claim_legacy=not strict)
        if cx.lat is not None and cx.lng is not None:
            skipped += 1
            continue
        # ①공부 주소(도로명→지번) 우선 — 동명 시설 오탐 원천 차단(v1.237)
        res = None
        for addr in _tx_address(db, name, lawd, dong):
            if not addr:
                continue
            hit = None
            if s.kakao_rest_api_key:
                hit = _kakao_query(s.kakao_rest_api_key, s.kakao_address_url or KAKAO_ADDRESS, addr)
            if not hit and naver_on:
                hit = _naver_query(s.naver_map_client_id, s.naver_map_client_secret, addr)
            if hit:
                res = (hit[0], hit[1], "address")
                break
        # ②주소 실패 시 기존 키워드·동 폴백
        if not res:
            res = geocode_one(s, name, lawd, dong, strict_dong=strict)
        # 검증: 단지명 키워드 좌표가 소속 동 기준점에서 임계 초과 → 동 기준점으로 강등(왜곡 방지)
        if res and res[2] == "complex" and dong:
            ref = _dong_ref(s, lawd, dong, dong_refs)
            if ref and _km(res[0], res[1], ref[0], ref[1]) > _dong_threshold_km(s, dong):
                res = (ref[0], ref[1], "dong")
                demoted += 1
        # 구 경계 검증: 결과가 자기 구 밖이면 저장하지 않음(틀린 좌표 저장 금지 — 왜곡 없음)
        if res and _in_own_gu(lawd, res[0], res[1]) is False:
            res = None
        if res:
            cx.lat, cx.lng = res[0], res[1]
            done += 1
        else:
            failed += 1
    db.commit()
    if done or cleared:
        bump_data_version()  # 좌표 변경 → 지도(heatmap) 캐시 무효화
    logger.info("지오코딩: 신규 %s · 기존 %s · 실패 %s · 동폴백 %s · 재검증초기화 %s",
                done, skipped, failed, demoted, cleared)
    return {"geocoded": done, "cached": skipped, "failed": failed,
            "demoted_to_dong": demoted, "revalidate_cleared": cleared}


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
