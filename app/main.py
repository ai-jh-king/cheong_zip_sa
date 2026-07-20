"""
FastAPI 진입점 (M1 검증용 최소 API).
지침서 '1 백엔드 / N 프론트': 웹·앱이 공유할 단일 API. 비즈니스 로직은 여기 집중.

M1 엔드포인트:
  GET /health              상태/설정 확인 (키 노출 없이 설정여부만)
  GET /regions             청주 4개 구 + 코드 검증상태
  GET /transactions        정규화된 실거래 조회(필터)
  GET /stats/summary       구별 평균/건수 요약 (집계 예시; 왜곡방지 고지 포함)

⚠️ 모든 응답은 데이터 표본 여부(sample)·출처(source)를 함께 내려 화면이
   '참고용/모의데이터'를 구분 표기할 수 있게 한다.
"""
from __future__ import annotations
from statistics import mean

from pathlib import Path

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db, init_db
from app.data.region_codes import CHEONGJU_DISTRICTS
from app.models import Transaction
from app.api.dashboard import router as dashboard_router
from app.api.home import router as home_router
from app.api.complex import router as complex_router
from app.api.places import router as places_router
from app.api.landmarks import router as landmarks_router
from app.api.compare import router as compare_router
from app.api.subscription import router as subscription_router
from app.api.push import router as push_router
from app.api.landing import router as landing_router
from app.api.loan import router as loan_router
from app.api.favorites import router as favorites_router
from app.api.personal import router as personal_router
from app.api.auth import router as auth_router
from app.api.listings import router as listings_router
from app.api.inquiries import router as inquiries_router
from app.api.billing import router as billing_router
from app.api.map import router as map_router
from app.api.search import router as search_router
from app.api.admin import router as admin_router
from app.api.community import router as community_router, notif_router
from app.api.ops import router as ops_router
from app.api.legal import router as legal_router
from app.api.commute import router as commute_router
from app.api.onboarding import router as onboarding_router
from app.api.pricecheck import router as pricecheck_router
from app.api.price import router as price_router

app = FastAPI(title="청주 부동산 플랫폼 API", version="0.2.0 (M2)")
# 웹 UI 서빙 경로. 기본=레거시 app/web(현행 동작 불변). 컷오버 시 환경변수 WEB_DIR=frontend/dist 로 전환.
import os as _osw
WEB_DIR = Path(_osw.environ["WEB_DIR"]).resolve() if _osw.environ.get("WEB_DIR") else (Path(__file__).parent / "web")
# Vite dist(assets/ 보유)를 env로 "명시"했을 때만 SPA 정적 서빙 활성화 → 레거시(app/web)에선 절대 활성화되지 않음.
SPA_MODE = bool(_osw.environ.get("WEB_DIR")) and (WEB_DIR / "assets").is_dir()

# CORS: 기본 "*"(개발 편의). 운영은 CORS_ORIGINS 환경변수로 좁힐 것
#   예) CORS_ORIGINS="https://청주도메인,capacitor://localhost,https://localhost"
_cors_env = _osw.environ.get("CORS_ORIGINS", "").strip()
_allow_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 응답 gzip 압축(초기 로딩 전송량↓ — JS/CSS/HTML/JSON 약 65~70% 감소). 작은 응답은 제외.
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=600)
app.include_router(dashboard_router)
app.include_router(home_router)
app.include_router(complex_router)
app.include_router(places_router)
app.include_router(landmarks_router)
app.include_router(onboarding_router)
app.include_router(pricecheck_router)
app.include_router(loan_router)
app.include_router(favorites_router)
app.include_router(personal_router)
app.include_router(auth_router)
app.include_router(listings_router)
app.include_router(inquiries_router)
app.include_router(billing_router)
app.include_router(map_router)
app.include_router(search_router)
app.include_router(admin_router)
app.include_router(community_router)
app.include_router(notif_router)
app.include_router(ops_router)
app.include_router(legal_router)
app.include_router(price_router)
app.include_router(commute_router)
app.include_router(compare_router)
app.include_router(subscription_router)
app.include_router(push_router)
app.include_router(landing_router)


def _rl_rule(method: str, path: str, s):
    """(버킷, 분당한도) 또는 None. 한도 0이면 무제한(미적용)."""
    if method == "POST":
        if path == "/community/posts":
            return ("post", s.rate_limit_post_per_min)
        if path.startswith("/community/posts/") and path.endswith("/comments"):
            return ("comment", s.rate_limit_comment_per_min)
        if path.endswith("/report"):
            return ("report", s.rate_limit_report_per_min)
        if path == "/auth/dev-login" or path.startswith("/auth/login"):
            return ("auth", s.rate_limit_auth_per_min)
        if path == "/listings" or path == "/listings/upload":   # 업로드=디스크 DoS 방어(미보호였음)
            return ("listing", s.rate_limit_listing_per_min)
        if path == "/inquiries":
            return ("inquiry", s.rate_limit_inquiry_per_min)
        if path.startswith("/billing/"):
            return ("billing", s.rate_limit_billing_per_min)
        if path.startswith("/push/"):
            return ("push", s.rate_limit_push_per_min)
        if path == "/complex/quotes":                            # 배치 집계 남용 방어
            return ("search", s.rate_limit_search_per_min)
        if path in ("/me/recent", "/me/searches"):
            return ("personal", s.rate_limit_personal_per_min)
    elif method == "PUT":
        if path == "/me/prefs":                                  # device_id 기반 개인화 쓰기 남용 방어
            return ("personal", s.rate_limit_personal_per_min)
    elif method == "GET" and path == "/search":
        return ("search", s.rate_limit_search_per_min)
    return None


def _client_ip(request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def _rate_limit(request, call_next):
    s = get_settings()
    if getattr(s, "rate_limit_enabled", True):
        rule = _rl_rule(request.method, request.url.path, s)
        if rule and rule[1] > 0:
            from app.core.ratelimit import limiter
            from fastapi.responses import JSONResponse
            allowed, retry = limiter.hit(f"{rule[0]}:{_client_ip(request)}", rule[1], 60)
            if not allowed:
                return JSONResponse(
                    status_code=429, headers={"Retry-After": str(retry)},
                    content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                             "retry_after": retry})
    return await call_next(request)


@app.middleware("http")
async def _request_timing(request, call_next):
    import time
    import logging as _lg
    t0 = time.perf_counter()
    response = await call_next(request)
    dur_ms = (time.perf_counter() - t0) * 1000
    path = request.url.path
    if path not in ("/health",) and not path.startswith("/uploads"):
        _lg.getLogger("request").info("%s %s -> %s %.0fms",
                                      request.method, path, response.status_code, dur_ms)
    return response

# 매물 사진 로컬 저장본 정적 서빙(storage_backend=local). s3면 사용 안 함.
try:
    from fastapi.staticfiles import StaticFiles
    _settings = get_settings()
    if _settings.storage_backend == "local":
        import os as _os
        _os.makedirs(_settings.upload_dir, exist_ok=True)
        app.mount(_settings.upload_public_base, StaticFiles(directory=_settings.upload_dir), name="uploads")
except Exception as _e:  # noqa
    pass


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    """백엔드가 UI(index.html)를 직접 서빙 → 별도 프론트 빌드 불필요."""
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    """웹푸시 서비스워커. 스코프를 위해 루트(/sw.js)에서 서빙."""
    return FileResponse(WEB_DIR / "sw.js", media_type="application/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/config")
def config():
    """프론트가 쓰는 공개 설정만 노출. (네이버 지도 클라이언트 ID는 도메인 제한된 공개 키)"""
    s = get_settings()
    return {
        "naver_map_client_id": s.naver_map_client_id,   # 지도 표시용(공개 가능)
        "map_enabled": bool(s.naver_map_client_id),
        "aggregate_months": s.aggregate_months,          # 시세 집계 윈도우(개월) — 화면 표기용
    }
DISCLAIMER = "실거래가는 신고 지연·정정·해제가 있을 수 있는 참고용 정보이며 법적 효력이 없습니다. 자료: 국토교통부 실거래가."


def _auto_seed_commute(log):
    """전입자 온보딩(전략 창끝)은 통근 '직장' 거점에 의존. 0건이면 자동 시드(멱등·좌표 하드코딩·API키 불필요).
    시드 누락으로 온보딩 위저드 1단계가 빈 목록이 되는 사고를 부팅 시 자동 차단."""
    try:
        from app.db.session import SessionLocal
        from app.models import CommuteDestination
        from sqlalchemy import select, func as _f
        with SessionLocal() as db:
            n = db.scalar(select(_f.count()).select_from(CommuteDestination)
                          .where(CommuteDestination.category == "job")) or 0
        if n == 0:
            from scripts.seed_commute import seed
            added = seed()
            log.info("통근 거점 자동 시드 완료: 신규 %s건 — 전입자 온보딩 활성화", added)
    except Exception as e:  # noqa: BLE001
        log.warning("통근 거점 자동 시드 스킵(무시): %s", e)


@app.on_event("startup")
def _startup():
    from app.core.logging import setup_logging
    import logging
    s = get_settings()
    setup_logging(getattr(s, "log_level", "INFO"))
    log = logging.getLogger(__name__)
    # 프로덕션 안전 가드 — 미설정으로 인한 운영 사고를 부팅 시점에 차단.
    if s.is_production:
        if not s.jwt_secret:
            raise RuntimeError(
                "프로덕션(app_env=production)에서 JWT_SECRET 미설정 → 부팅 거부. "
                "다중 워커 환경에서 워커마다 임시키가 달라 로그인 토큰이 무작위로 무효화됩니다. "
                "32자 이상 랜덤 문자열을 JWT_SECRET 환경변수로 설정하세요.")
        if s.auth_dev_login:
            raise RuntimeError(
                "프로덕션에서 AUTH_DEV_LOGIN=true → 부팅 거부. /auth/dev-login 은 키·OAuth 없이 "
                "임의 계정(중개사 권한 포함)을 발급하는 인증 우회 백도어입니다. AUTH_DEV_LOGIN=false 로 설정하세요.")
        if _allow_origins == ["*"]:
            log.warning("⚠️ 프로덕션 CORS_ORIGINS 미설정(*) — 배포 도메인으로 좁히세요. 예) CORS_ORIGINS=https://your-domain,capacitor://localhost")
    init_db()
    if s.auto_seed_commute:
        _auto_seed_commute(log)
    # 에러 모니터링(Sentry) — DSN 설정 시에만. 패키지 없으면 조용히 건너뜀.
    dsn = (get_settings().sentry_dsn or "").strip()
    if dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0, send_default_pii=False)
            logging.getLogger(__name__).info("Sentry 에러 모니터링 활성")
        except Exception:  # noqa
            logging.getLogger(__name__).warning("Sentry 초기화 실패(무시) — sentry-sdk 미설치?")

    # 진입 속도 개선: 시작 시 홈 집계를 백그라운드로 미리 계산(캐시 워밍업).
    # 첫 사용자가 무거운 재계산을 기다리지 않도록. 실패해도 서비스에 영향 없음.
    def _warm_cache():
        try:
            from app.db.session import SessionLocal
            from app.services import stats
            from app.services.geocode import coords_map
            db = SessionLocal()
            try:
                coords_map(db)   # /dashboard/ranking 매 요청 풀스캔이던 것(캐시 프리워밍)
                for pt in ("apartment",):
                    # /dashboard/board
                    stats.city_summary(db, pt)
                    stats.city_trend(db, pt, 12)
                    stats.gu_price_ranking(db, pt)
                    stats.recent_trades(db, pt, 4)
                    stats.trend(db, pt, 12)
                    stats.trending_complexes(db, pt, 50)
                    stats.landmark_apts(db, pt, 50)
                    stats.top_movers(db, pt, 10)
                    stats.landmark_by_band(db, pt, 5)
                    # /dashboard/ranking (프런트 첫 로드 limit=60, area_band=all) — 미커버였음
                    stats.top_trades(db, pt, 60, "all")
                    stats.top_trades_by_ppm(db, pt, 60, "all")
                    stats.complex_movers(db, pt, 10)
                    stats.newly_high(db, pt, 10)
                    stats.newly_low(db, pt, 10)
                    stats.active_regions(db, "all")
                    # /home/feed
                    stats.ppm_by_area(db, pt)
                    stats.volume(db, pt)
                logging.getLogger(__name__).info("캐시 워밍업 완료")
            finally:
                db.close()
        except Exception:  # noqa
            logging.getLogger(__name__).warning("캐시 워밍업 실패(무시)")
    import threading as _wth
    _wth.Thread(target=_warm_cache, daemon=True).start()


@app.get("/health")
def health(db: Session = Depends(get_db)):
    s = get_settings()
    # DB 핑(실제 연결 확인) — 모니터링이 DB 장애를 잡도록.
    db_ok = True
    try:
        db.execute(select(func.count()).select_from(Transaction).limit(1))
    except Exception:
        db_ok = False
    # 데이터 신선도(마지막 수집 시각)
    last_collect_at = None
    try:
        from app.services import appmeta
        lc = appmeta.get_json(db, "last_collect")
        last_collect_at = lc.get("at") if lc else None
    except Exception:
        pass
    from app.core.cache import get_data_version
    # 키 '값'은 절대 노출하지 않고 설정 여부만 보고.
    return {
        "status": "ok" if db_ok else "degraded",
        "db_ok": db_ok,
        "env": s.app_env,
        "db": "sqlite(local)" if s.effective_database_url.startswith("sqlite") else "configured",
        "data_version": get_data_version(),
        "last_collect_at": last_collect_at,
        "keys_configured": {
            "molit": s.molit_enabled,
            "applyhome": bool(s.applyhome_service_key),
            "kakao_map": bool(s.kakao_js_map_key or s.kakao_rest_api_key),
            "finlife": bool(s.finlife_api_key),
            "hf": bool(s.hf_api_key),
        },
        "feature_flags": {
            "ads": s.feature_ads,
            "monetization": s.feature_monetization,
            "curated_insights": s.feature_curated_insights,
            "billing": s.feature_billing,
        },
    }


@app.get("/regions")
def regions():
    return {
        "disclaimer": "법정동코드는 실제 API 응답으로 검증 필요(verified 필드 확인).",
        "regions": [
            {"code": d.code, "name": f"청주시 {d.name}", "verified": d.verified}
            for d in CHEONGJU_DISTRICTS
        ],
    }


@app.get("/transactions")
def transactions(
    db: Session = Depends(get_db),
    region: str | None = Query(None, description="법정동코드 5자리"),
    property_type: str | None = Query(None, description="apartment/officetel/rowhouse/detached"),
    deal_type: str | None = Query(None, description="trade/jeonse/wolse"),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0, description="페이지네이션 오프셋(0=처음). limit과 함께 더보기/다음페이지에 사용"),
):
    stmt = select(Transaction)
    if region:
        stmt = stmt.where(Transaction.lawd_cd == region)
    if property_type:
        stmt = stmt.where(Transaction.property_type == property_type)
    if deal_type:
        stmt = stmt.where(Transaction.deal_type == deal_type)
    stmt = stmt.order_by(Transaction.contract_date.desc()).offset(offset).limit(limit)
    rows = db.scalars(stmt).all()

    any_sample = any(r.is_sample for r in rows)
    return {
        "disclaimer": DISCLAIMER,
        "contains_sample_data": any_sample,
        "count": len(rows),
        "offset": offset,
        "has_more": len(rows) >= limit,  # 다음 페이지 존재 가능성(더보기 노출용)
        "items": [
            {
                "lawd_cd": r.lawd_cd,
                "property_type": r.property_type, "deal_type": r.deal_type,
                "complex_name": r.complex_name, "dong": r.dong_name,
                "exclusive_area": r.exclusive_area, "floor": r.floor,
                "contract_date": r.contract_date.isoformat() if r.contract_date else None,
                "deal_amount": r.deal_amount, "deposit": r.deposit,
                "monthly_rent": r.monthly_rent,
                "source": r.source, "is_sample": r.is_sample,
                # 면적당 단가(만원/㎡) 자동 환산 — 매매가 있을 때만, 없으면 null(지어내지 않음)
                "price_per_m2": round(r.deal_amount / r.exclusive_area, 1)
                if (r.deal_amount and r.exclusive_area) else None,
            }
            for r in rows
        ],
    }


@app.get("/stats/summary")
def stats_summary(db: Session = Depends(get_db),
                  property_type: str = Query("apartment")):
    """구별 매매 평균가·건수 요약(집계 예시). 표본 적으면 평균은 신뢰 낮음을 명시."""
    out = []
    for d in CHEONGJU_DISTRICTS:
        amounts = db.scalars(
            select(Transaction.deal_amount).where(
                Transaction.lawd_cd == d.code,
                Transaction.property_type == property_type,
                Transaction.deal_type == "trade",
                Transaction.deal_amount.isnot(None),
            )
        ).all()
        out.append({
            "region": f"청주시 {d.name}", "code": d.code,
            "trade_count": len(amounts),
            "avg_deal_amount": round(mean(amounts)) if amounts else None,
            "low_sample_warning": len(amounts) < 5,  # 표본 부족 경고
        })
    return {
        "disclaimer": DISCLAIMER + " 평균은 표본 수가 적으면 변동성이 큽니다.",
        "property_type": property_type,
        "by_region": out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SPA 정적 서빙 (컷오버용) — 환경변수 WEB_DIR=frontend/dist 로 dist를 가리킬 때만 활성화.
# 위의 모든 명시 라우트(/, /sw.js, /config, /health, /transactions ...)와 라우터가
# 먼저 등록되어 우선 매칭되고, 이 마운트는 그 외 정적 경로(/assets/*, /manifest.webmanifest,
# /icons/* 등)만 처리한다. 레거시(app/web)에선 SPA_MODE=False → 마운트하지 않음(동작 불변).
if SPA_MODE:
    from fastapi.staticfiles import StaticFiles as _StaticFiles

    class _CachedSPA(_StaticFiles):
        """해시된 자산(/assets/*)은 1년 immutable 캐시(재방문 즉시 로딩), 그 외는 no-cache."""
        async def get_response(self, path, scope):
            resp = await super().get_response(path, scope)
            try:
                if path.startswith("assets/") or path.startswith("assets\\"):
                    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                else:
                    # index.html·manifest·아이콘 등(미해시) → 항상 재검증(업데이트 즉시 반영)
                    resp.headers["Cache-Control"] = "no-cache"
            except Exception:
                pass
            return resp

    app.mount("/", _CachedSPA(directory=WEB_DIR, html=True), name="spa")
