"""
중앙 설정 로더.
- 모든 키/비밀은 .env 에서만 읽는다. 코드에 하드코딩 금지 (지침서 9장).
- 규제 파라미터(LTV/DSR)는 여기 두지 않고 별도 설정/DB(LoanRule)로 분리한다.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- 실행 환경 ---
    app_env: str = "local"
    log_level: str = "INFO"

    # --- DB ---
    # 비어 있으면 로컬 SQLite 로 폴백 → 키 없이도 즉시 구동 가능.
    database_url: str = ""

    # --- 공공데이터포털: 국토부 실거래가 ---
    molit_service_key: str = ""

    # --- 청약홈 / 지도 / 뉴스 / 금융 (후속 마일스톤) ---
    applyhome_service_key: str = ""
    academy_service_key: str = ""   # NEIS(open.neis.go.kr) 학원교습소 API 키. data.go.kr 키와 다름!
    applyhome_competition_url: str = ""   # (선택) 청약홈 경쟁률·당첨가점 오픈API 엔드포인트(검증 후 입력 시 실연동)
    kakao_rest_api_key: str = ""
    kakao_js_map_key: str = ""
    naver_map_client_id: str = ""
    naver_map_client_secret: str = ""
    naver_search_client_id: str = ""
    naver_search_client_secret: str = ""
    finlife_api_key: str = ""
    hf_api_key: str = ""
    hf_policy_api_url: str = ""   # (선택) HF 정책대출 금리 오픈API 엔드포인트(검증 후 입력 시 실연동)
    seomin_api_key: str = ""
    seomin_api_url: str = ""   # (선택) 서민금융 '서민금융 한눈에' 오픈API 엔드포인트(검증 후 입력 시 실연동)
    # 생활시설(Place) 표준데이터 오픈API 엔드포인트 — 활용신청 후 '내 API 페이지'의 실제 URL(uddi 포함)을 입력.
    # 미설정이면 해당 시설은 수집하지 않음(가짜 URL 호출 금지 = 왜곡 방지). 검증된 데이터셋 ID는 DATA_PLACES.md 참조.
    places_daycare_url: str = ""   # 전국어린이집표준데이터(15013108) — 위경도·정원·현원 포함(검증)
    places_sports_url: str = ""    # 전국공공시설개방정보/체육시설표준데이터(15013117 등)
    places_library_url: str = ""   # 전국도서관표준데이터(15013109)
    places_medical_url: str = ""   # 전국의료기관표준데이터(15096293) — 좌표 EPSG:5174 주의
    # --- 개인화 2단계: 소셜 로그인(구조만, 키 설정 시 활성화) ---
    kakao_login_rest_key: str = ""        # 카카오 로그인 REST 키(지도 키와 별개 앱일 수 있음)
    kakao_login_client_secret: str = ""   # 카카오 콘솔 '보안 > Client Secret 사용' ON 한 경우만 설정. OFF면 비워둠(있어도 무해)
    naver_login_client_id: str = ""       # 네이버 로그인 Client ID(검색/지도 키와 별개)
    naver_login_client_secret: str = ""
    auth_redirect_base: str = ""          # OAuth 리다이렉트 base URL(배포 도메인)
    jwt_secret: str = ""                   # 세션 토큰 서명키(배포 시 필수 설정)
    session_days: int = 14                 # 세션 유효기간(일)
    auth_dev_login: bool = True            # 개발용 로그인 허용(운영 배포 시 False 권장)
    auto_seed_commute: bool = True         # 부팅 시 통근 거점 0건이면 자동 시드(전입자 온보딩=전략 창끝 활성화). 테스트는 false
    auto_geocode: bool = True              # 수집 후 단지 좌표 자동 지오코딩(키 있을 때만)
    geocode_use_naver: bool = False        # 지오코딩 제공자: 기본 카카오 단독. true 면 네이버 우선+카카오 폴백
    geocode_seed_limit: int = 0            # 0=제한없음(전체). 쿼터 보호용 상한
    # 레이트리밋(어뷰징/스팸 방어) — 분당 IP 기준. 0=해당 버킷 무제한
    rate_limit_enabled: bool = True
    rate_limit_auth_per_min: int = 10        # 로그인 시작/개발로그인
    rate_limit_post_per_min: int = 20        # 글쓰기
    rate_limit_comment_per_min: int = 30     # 댓글
    rate_limit_report_per_min: int = 30      # 신고
    rate_limit_search_per_min: int = 60      # 검색
    rate_limit_listing_per_min: int = 10     # 매물 등록
    rate_limit_inquiry_per_min: int = 6      # 매물 문의(연락처 포함 → 스팸·PII 보호)
    rate_limit_billing_per_min: int = 20     # 결제 시작/확인

    # 단지 기본정보 보강(공동주택관리정보 K-apt) — data.go.kr 공통키 사용. Swagger 로 URL 확정.
    # 미설정(빈 값) 시 보강 건너뜀(절대 날조하지 않음).
    kapt_list_url: str = ""   # 시군구 단지목록(kaptCode). 예: http://apis.data.go.kr/1613000/AptListService3/getSigunguAptList
    kapt_info_url: str = ""   # 단지 기본정보. 예: http://apis.data.go.kr/1613000/AptBasisInfoServiceV3/getAphusBassInfoV3

    # === 외부 API 엔드포인트(URL) ===
    # 공급사 정책/도메인 이전으로 바뀔 수 있어 .env 로 덮어쓸 수 있게 분리. 빈 값이면 코드 기본값 사용.
    molit_base_url: str = "https://apis.data.go.kr/1613000"          # 실거래가 베이스(+operation path)
    naver_geocode_url: str = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"  # 신 Maps 게이트웨이
    kakao_keyword_url: str = "https://dapi.kakao.com/v2/local/search/keyword.json"
    kakao_address_url: str = "https://dapi.kakao.com/v2/local/search/address.json"
    kakao_category_url: str = "https://dapi.kakao.com/v2/local/search/category.json"
    finlife_base_url: str = "https://finlife.fss.or.kr/finlifeapi"
    applyhome_url: str = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"
    news_url: str = "https://openapi.naver.com/v1/search/news.json"
    # 소셜 로그인(OAuth) 엔드포인트
    kakao_token_url: str = "https://kauth.kakao.com/oauth/token"
    kakao_userinfo_url: str = "https://kapi.kakao.com/v2/user/me"
    kakao_authorize_url: str = "https://kauth.kakao.com/oauth/authorize"
    naver_token_url: str = "https://nid.naver.com/oauth2.0/token"
    naver_userinfo_url: str = "https://openapi.naver.com/v1/nid/me"
    naver_authorize_url: str = "https://nid.naver.com/oauth2.0/authorize"

    # --- 운영(관리자·스케줄러) ---
    admin_token: str = ""                  # 관리자 API 토큰(미설정 시 관리자 API 비활성)
    scheduler_interval_hours: int = 24     # 독립 스케줄러 수집+지오코딩 주기(시간)
    scheduler_run_collect: bool = True     # 스케줄러가 수집(live)도 수행할지
    # --- 관측성(모니터링·경보) ---
    sentry_dsn: str = ""                   # 설정 시 에러 모니터링(Sentry) 활성
    alert_webhook_url: str = ""            # 설정 시 작업 실패를 Slack/Discord 등으로 경보
    data_stale_days: int = 3               # 실데이터가 이 일수보다 오래되면 경고
    # --- 백업 ---
    backup_dir: str = "backups"            # 백업 파일 저장 폴더
    backup_keep: int = 14                  # 최근 N개만 보관(이후 자동 삭제)
    scheduler_run_backup: bool = True      # 스케줄러 사이클마다 DB 백업 수행
    # --- 공유/SEO ---
    public_base_url: str = ""              # 예: https://cheongju.example.com (OG·sitemap 절대 URL). 비면 요청 기반 추론
    # --- 외부 API 응답 캐시 TTL(초). 매 요청 외부호출 방지 + 레이트리밋 보호 ---
    cache_ttl_stats_sec: int = 600        # 시세 집계 캐시(10분, 수집 시 즉시 무효화)
    cache_ttl_loan_sec: int = 21600       # 대출 금리(6시간)
    cache_ttl_news_sec: int = 600         # 뉴스(10분)
    cache_ttl_subs_sec: int = 1800        # 청약/분양(30분)

    # --- 알림 ---
    email_provider: str = ""
    sendgrid_api_key: str = ""
    fcm_server_key: str = ""
    kakao_alimtalk_sender_key: str = ""
    kakao_alimtalk_api_key: str = ""
    # 웹푸시(VAPID) — 키 둘 다 있을 때만 푸시 활성. 생성: `python -m scripts.gen_vapid`
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@cheongju-realestate.local"

    # --- 사진 스토리지(매물 이미지) ---
    storage_backend: str = "local"          # local | s3
    upload_dir: str = "app/web/uploads"     # local 저장 경로(정적 서빙)
    upload_public_base: str = "/uploads"    # local 공개 URL base
    upload_max_mb: int = 8
    s3_bucket: str = ""
    s3_region: str = ""
    s3_endpoint_url: str = ""               # MinIO 등 S3 호환 스토리지(선택)
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_public_base_url: str = ""            # CDN/공개 base(있으면 우선 사용)

    # --- 수집 파이프라인 동작값 ---
    molit_rate_limit_per_sec: float = 4.0
    molit_request_timeout: float = 15.0
    collect_months_back: int = 12
    aggregate_months: int = 12          # 집계 기본 윈도우(개월). 시세 중앙값/평단가/전세가율 등 '현재 시세'는 최근 N개월만 사용

    # ----- 통근권/생활권 (M-commute) -----
    commute_enabled: bool = True
    kakao_directions_url: str = "https://apis-navi.kakaomobility.com/v1/directions"  # 카카오모빌리티 길찾기(자동차). 헤더 Authorization: KakaoAK <REST키>
    commute_default_mode: str = "car"           # car/transit
    commute_avg_kmh_car: float = 38.0           # 직선거리→시간 추정용 평균속도(자동차, 도심 보정)
    commute_avg_kmh_transit: float = 22.0       # 대중교통 평균속도 추정
    commute_detour_factor: float = 1.3          # 직선거리 → 실도로 우회 보정 계수
    commute_max_minutes_default: int = 40       # 검색 기본 상한(분)
    commute_cache_ttl_days: int = 30            # 캐시 신선도(일). 지났으면 배치 재계산 대상

    # --- 피처 플래그 (부록 B) ---
    feature_ads: bool = False
    feature_monetization: bool = False
    feature_curated_insights: bool = False
    feature_billing: bool = False                 # 결제/구독 시스템 노출(기본 OFF=현재와 동일)
    billing_provider: str = "mock"                # mock | toss | portone (키 없으면 mock)

    @property
    def effective_database_url(self) -> str:
        """DATABASE_URL 미설정 시 로컬 SQLite 파일로 폴백.
        설정 시 postgres://·postgresql:// 는 psycopg3 드라이버로 정규화(관리형 DB URL 호환)."""
        if self.database_url:
            return self._normalize_db_url(self.database_url)
        return "sqlite:///./cheongju_local.db"

    @staticmethod
    def _normalize_db_url(url: str) -> str:
        if url.startswith("postgres://"):          # Heroku/일부 제공자 형식
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):         # 드라이버 미지정 → psycopg3 사용
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def is_production(self) -> bool:
        """운영 배포 여부(app_env=prod|production). 부팅 안전 가드(JWT 필수 등)에 사용."""
        return self.app_env.strip().lower() in ("prod", "production")

    @property
    def molit_enabled(self) -> bool:
        return bool(self.molit_service_key)

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
