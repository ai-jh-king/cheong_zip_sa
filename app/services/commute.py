"""통근권 계산·검색 서비스.

설계(운영·확장):
  - 통근시간은 (단지×목적지×수단) 캐시(CommuteTime)에서 읽는다 → 빠른 'N분 이내' 검색.
  - 계산 방법(정확도 라벨 = method):
      · 'api'      : 카카오모빌리티 길찾기(자동차) 실측 소요시간(키 있을 때).
      · 'haversine': 직선거리 × 우회계수 ÷ 평균속도 추정(키 없거나 대중교통/도보).
  - 콜드스타트: 캐시가 비면 검색 시 즉석 haversine 추정으로 동작 → 배치(scripts.compute_commute)
    실행 후 'api' 값으로 자동 대체. '왜곡 없음': 추정/실측을 method 로 명확히 구분 노출.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from math import radians, sin, cos, asin, sqrt

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Complex, CommuteDestination, CommuteTime

logger = logging.getLogger(__name__)


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 직선거리(미터)."""
    r = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lng2 - lng1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _avg_kmh(mode: str, s) -> float:
    return s.commute_avg_kmh_transit if mode == "transit" else s.commute_avg_kmh_car


def estimate_haversine(o_lat, o_lng, d_lat, d_lng, mode: str) -> tuple[int, int]:
    """직선거리 추정 → (minutes, distance_m). 우회계수·평균속도 보정."""
    s = get_settings()
    straight = haversine_m(o_lat, o_lng, d_lat, d_lng)
    road = straight * s.commute_detour_factor
    kmh = _avg_kmh(mode, s)
    minutes = int(round(road / 1000.0 / max(kmh, 1.0) * 60))
    return max(minutes, 1), int(round(road))


def kakao_directions_minutes(o_lat, o_lng, d_lat, d_lng) -> tuple[int, int] | None:
    """카카오모빌리티 길찾기(자동차) 실측 → (minutes, distance_m). 실패 시 None."""
    s = get_settings()
    if not s.kakao_rest_api_key:
        return None
    try:
        r = httpx.get(
            s.kakao_directions_url,
            params={"origin": f"{o_lng},{o_lat}", "destination": f"{d_lng},{d_lat}"},
            headers={"Authorization": f"KakaoAK {s.kakao_rest_api_key}"},
            timeout=8.0,
        )
        r.raise_for_status()
        routes = r.json().get("routes") or []
        if not routes:
            return None
        summary = routes[0].get("summary") or {}
        dur = summary.get("duration")        # 초
        dist = summary.get("distance")       # m
        if dur is None:
            return None
        return max(int(round(dur / 60)), 1), int(dist or 0)
    except Exception as e:  # noqa: BLE001
        logger.debug("kakao directions 실패: %s", e)
        return None


def compute_one(o_lat, o_lng, d_lat, d_lng, mode: str) -> dict:
    """단일 (출발×도착×수단) 계산. mode=car 이고 키 있으면 실측, 아니면 추정."""
    if mode == "car":
        api = kakao_directions_minutes(o_lat, o_lng, d_lat, d_lng)
        if api:
            return {"minutes": api[0], "distance_m": api[1], "method": "api", "source": "KAKAO_DIRECTIONS"}
    minutes, dist = estimate_haversine(o_lat, o_lng, d_lat, d_lng, mode)
    return {"minutes": minutes, "distance_m": dist, "method": "haversine", "source": None}


def list_destinations(db: Session) -> list[dict]:
    rows = db.scalars(
        select(CommuteDestination)
        .where(CommuteDestination.is_active.is_(True))
        .order_by(CommuteDestination.sort_order, CommuteDestination.id)
    ).all()
    return [{
        "id": d.id, "key": d.key, "name": d.name, "category": d.category,
        "gu": d.gu, "lat": d.lat, "lng": d.lng,
        "has_coord": (d.lat is not None and d.lng is not None),
        "coord_method": d.coord_method,
    } for d in rows]


def search_by_commute(db: Session, dest_id: int, mode: str, max_minutes: int,
                      property_type: str | None = None, limit: int = 60) -> dict:
    """목적지까지 max_minutes 이내 단지. 캐시 우선, 없으면 즉석 haversine 추정.

    반환: {destination, mode, results:[{complex_id, name, gu, lat, lng, minutes, method, property_type}], method_summary}
    """
    dest = db.get(CommuteDestination, dest_id)
    if not dest or dest.lat is None or dest.lng is None:
        return {"found": False, "reason": "목적지 좌표 없음"}

    cached = {c.complex_id: c for c in db.scalars(
        select(CommuteTime).where(CommuteTime.destination_id == dest_id, CommuteTime.mode == mode)
    ).all()}

    q = select(Complex).where(Complex.lat.isnot(None), Complex.lng.isnot(None))
    if property_type:
        q = q.where(Complex.property_type == property_type)
    complexes = db.scalars(q).all()

    out = []
    used_methods = set()
    for cx in complexes:
        hit = cached.get(cx.id)
        if hit and hit.minutes is not None:
            minutes, method = hit.minutes, hit.method
        else:
            est = compute_one(cx.lat, cx.lng, dest.lat, dest.lng, mode)  # 즉석 추정(보통 haversine)
            minutes, method = est["minutes"], est["method"]
        if minutes is not None and minutes <= max_minutes:
            out.append({
                "complex_id": cx.id, "name": cx.name, "lawd_cd": cx.lawd_cd, "gu": _gu(cx.lawd_cd),
                "lat": cx.lat, "lng": cx.lng, "property_type": cx.property_type,
                "minutes": minutes, "method": method,
            })
            used_methods.add(method)
    out.sort(key=lambda r: r["minutes"])
    out = out[:limit]

    # 결과 단지의 최근 N개월 중앙 매매가 결합(있으면) — '시간 + 가격' 의사결정용
    if out:
        from statistics import median as _median
        from app.models import Transaction
        from app.services.stats import _cutoff_date
        ids = [r["complex_id"] for r in out]
        price_map: dict[int, list[int]] = {}
        for t in db.scalars(select(Transaction).where(
                Transaction.complex_id.in_(ids), Transaction.deal_type == "trade",
                Transaction.is_canceled.isnot(True),
                Transaction.contract_date >= _cutoff_date())).all():
            if t.deal_amount:
                price_map.setdefault(t.complex_id, []).append(t.deal_amount)
        for r in out:
            vals = price_map.get(r["complex_id"])
            r["price"] = round(_median(vals)) if vals else None
    return {
        "found": True,
        "destination": {"id": dest.id, "name": dest.name, "category": dest.category,
                        "lat": dest.lat, "lng": dest.lng},
        "mode": mode, "max_minutes": max_minutes,
        "method_summary": ("실측(길찾기)" if used_methods == {"api"} else
                           "추정(직선거리)" if used_methods == {"haversine"} else
                           "혼합(실측+추정)" if used_methods else "—"),
        "results": out,
        "count": len(out),
    }


def _gu(lawd_cd: str) -> str:
    from app.data.region_codes import DISTRICT_BY_CODE
    return DISTRICT_BY_CODE.get(str(lawd_cd), "")


def hub_access(db: Session, lat: float, lng: float, limit_per_cat: int = 3) -> list[dict] | None:
    """단지 좌표 → 청주 주요 직장·거점까지 직선거리(km).
    통근권 목적지(CommuteDestination)를 재사용해 좌표 일관성 유지.
    목적지 미시드/좌표 없음이면 None(프런트 숨김, 왜곡 없음). 직선거리임을 라벨로 명시할 것."""
    if lat is None or lng is None:
        return None
    rows = db.scalars(select(CommuteDestination).where(
        CommuteDestination.is_active.is_(True),
        CommuteDestination.lat.isnot(None), CommuteDestination.lng.isnot(None),
    ).order_by(CommuteDestination.sort_order)).all()
    if not rows:
        return None
    out = []
    for d in rows:
        km = round(haversine_m(lat, lng, d.lat, d.lng) / 1000, 1)
        out.append({"key": d.key, "name": d.name, "category": d.category,
                    "distance_km": km, "coord_method": d.coord_method or "seed_approx"})
    # 카테고리별 가까운 순 상한(직장은 전부, 나머지는 limit)
    out.sort(key=lambda x: x["distance_km"])
    seen: dict = {}
    trimmed = []
    for h in out:
        c = h["category"]
        seen[c] = seen.get(c, 0) + 1
        if c == "job" or seen[c] <= limit_per_cat:
            trimmed.append(h)
    return trimmed
