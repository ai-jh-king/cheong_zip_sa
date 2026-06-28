# CLAUDE.md — 청주 부동산 플랫폼 (Claude Code 작업 안내)

> **Claude Code가 이 저장소를 이어서 개발할 때 가장 먼저 읽는 규칙·맥락 파일.**
> 새 작업 전에 이 문서와 `skills/`, 그리고 진행현황 SSOT인 `ROADMAP.md`를 먼저 읽으세요.

## 0. Claude Code 작업 방식 (중요)
- 이제 **실제 파일시스템에서 직접 수정·실행**합니다. (과거 샌드박스의 zip/outputs 복사 루틴은 **불필요**.)
- 흐름: 파일 수정 → 아래 6의 검증 → `python run.py`로 스모크 테스트 → 커밋.
- 한 번에 **하나의 기능만** 차근차근. 시작·완료 시 `ROADMAP.md`의 체크박스를 갱신.
- 불명확하면 임의 가정 대신 "확인 필요"로 남기고, 외부 API 필드는 추측하지 말 것.

## 1. 프로젝트 개요
충북 **청주시(상당 43111 / 서원 43112 / 흥덕 43113 / 청원 43114)** 부동산 정보 플랫폼.
실수요자가 시세·추이·청약·뉴스·정책·대출·세금을 **한 화면에서** 비교하고, 커뮤니티까지 제공.
매물: 아파트·오피스텔·빌라·단독다가구 / 거래: 매매·전세·월세. **응답·주석·UI는 한국어.**

## 2. 절대 원칙 (위반 금지)
1. **왜곡 없음**: API 필드·수치를 추측/창작하지 않음. 없는 값은 `None`/"표본 부족". 예시·모의는 `is_sample`/배지로 구분.
2. **공식 소스만**: 공공 API·정식 제휴만. 타 서비스 스크래핑 금지.
3. **참고용 고지**: 실거래·대출·세금은 "참고용 추정치". 금융/세무 자문 아님. "승인/최저금리 보장" 금지.
4. **개인정보 최소**: 기본 익명 `device_id`. 민감정보(소득·신용)는 동의·비중앙저장.
5. **설정값 분리**: 규제·요율(LTV/DSR·세금·중개보수·캐시 TTL)은 하드코딩 금지 → 설정/룰.
6. **확장 대비**: 신규 지역/유형은 코드·설정 추가만으로. 외부 응답은 tolerant 매핑 + "⚠️ Swagger 확인" 주석.

## 3. 기술 스택 / 아키텍처
- **백엔드**: Python · FastAPI · SQLAlchemy 2.0. 계층: `api / services / sources / pipeline / models / data`.
- **프런트**: 권위 소스 = **`frontend/src/main.jsx`**(React 18 · Vite). 레거시 `app/web/index.html`(Babel CDN·빌드 없음)은 **동결**(폴백 잔존). 백엔드 미연결 시 DEMO 폴백. (상세는 다음 항목)
- **프런트 — 단일 소스(컷오버 확정)**: 웹 UI의 권위 소스는 **`frontend/src/`(Vite)**. 모든 UI/기능 수정은 **여기서만** → `npm run build` → 배포(웹·PWA·Capacitor가 같은 `dist` 공유). `app/web/index.html`(레거시)은 **동결 — 편집 금지**, bare 로컬 실행의 폴백으로만 잔존(한 배포 사이클 후 제거 예정).
  - **서빙**: `app/main.py`의 `WEB_DIR` 환경변수. **프로덕션 이미지는 멀티스테이지 Dockerfile이 프런트를 빌드하고 `WEB_DIR=/app/frontend/dist`로 dist를 서빙**(컷오버 확정). bare 로컬에서 미설정 시 레거시 폴백. dist 지정 시 `SPA_MODE`로 `/assets`·manifest·icons 정적 마운트(명시 라우트·API 우선). 절차·검증·롤백: **`CUTOVER.md`**. 상세: `MOBILE_APP_STRATEGY.md`·`frontend/README.md`.
- **DB**: 기본 SQLite ↔ `DATABASE_URL` 설정 시 PostgreSQL. **Alembic이 운영 스키마 권위 소스**(0001→0002 baseline).
- **캐시**: `app/core/cache.py` — 외부호출 `@ttl_cached`, **시세 집계는 `@stat_cached`(데이터 버전 기반)**.
- 비즈니스 로직(시세집계·대출·세금)은 **백엔드 집중**, 프런트는 표시/입력만. "1 백엔드 N 프론트".

### 확장성 관련 핵심 규약 (대규모 운영 대비)
- **카운터는 원자적으로**: 조회수·좋아요·댓글수·신고수 등은 read-modify-write 금지 → `update(...).values(x=func.coalesce(x,0)±1)`. (community.py 참고)
- **무거운 집계는 캐시**: 새 집계 함수(첫 인자 `db`)는 `@stat_cached()` 적용. 원천 데이터가 바뀌는 경로(collect/geocode)에서 `bump_data_version()` 호출로 무효화.
- **스키마 변경은 Alembic**: `create_all` 의존 금지. 모델 수정 후 `alembic revision --autogenerate` → 검토 → 배포 시 `python -m scripts.db_upgrade`.

## 4. 레포 구조 (핵심)
```
app/
  main.py                FastAPI + 라우터 등록 + UI("/")
  core/config.py         설정(.env), effective_database_url, 캐시 TTL
  core/cache.py          TTL 캐시 + stat_cached(데이터버전 집계 캐시) + bump_data_version
  core/security.py       표준 라이브러리 JWT(세션/OAuth state)
  db/session.py          엔진/세션, init_db(+_ensure_columns 안전망)
  data/region_codes.py   청주 4개 구 + 구 중심좌표(DISTRICT_CENTROIDS)
  models/__init__.py     ORM 전체(아래 5)
  sources/molit/         실거래 8종(endpoints/client/normalize)
  sources/{applyhome,news,finlife,hf,seomin}.py
  pipeline/collect.py    수집·정규화·dedup upsert·캐시 무효화
  services/{stats,loan,costs,geocode,poi,storage}.py
  api/{dashboard,home,complex,loan,favorites,personal,   # 시세·대출·개인화
       auth,listings,search,admin,community}.py          # 로그인·매물·검색·관리자·게시판(+notif_router)
  web/index.html         단일 React UI(DEMO 폴백)
  fixtures/              오프라인 검증 표본(is_sample)
frontend/                웹 빌드(Vite): 정본 src/main.jsx + PWA(manifest·아이콘·SW). build→dist(운영 서빙). 컷오버 구성 완료(멀티스테이지)
scripts/                 run_collect / geocode / scheduler / db_upgrade / verify_region_codes
migrations/              Alembic (env.py가 앱 설정 URL 사용)
skills/                  ★ 모듈별 상세지침(아래 9)
```

## 5. 데이터 모델
`Region` · `Complex` · `Transaction`(dedup_key 유니크·raw_payload 보존) · `Favorite` · `UserPref` · `RecentView` · `SavedSearch` · `Account` · `DeviceLink` · `Listing` · `Post` · `Comment`(parent_id 대댓글) · `PostLike`(uq post+owner) · `ReportLog`(uq target+owner) · `Notification`(account_id 인덱스·type comment/reply/transaction/new_high) · `Bookmark`(uq owner+post) · `CommuteDestination`·`CommuteTime`(통근) · `PushSubscription`(웹푸시 구독·endpoint 유니크) · `JobRun`(배치 실행 이력).

## 6. 수정 후 필수 검증 루틴 (반드시 실행)
**프런트(`frontend/src/main.jsx`) 수정 시 — 표준 검증**: 괄호 균형(`()`·`{}`·`[]` 모두 0) + `verify_frontend`. **모든 UI 수정은 여기서만**(레거시 `app/web/index.html`은 **동결 — 편집 금지**, 폴백 잔존):
```bash
python3 -c "
c=open('frontend/src/main.jsx').read()
for o,cl in [('(',')'),('{','}'),('[',']')]:
    print(o+cl,'OK' if c.count(o)==c.count(cl) else 'MISMATCH')
"
python -m scripts.verify_frontend   # 괄호·React/ReactDOM import 커버·index.html 구성, PASS 기대
```
**백엔드 수정 시**: `python -m py_compile app/<바꾼파일>.py` (또는 전체 `python -m compileall app`).
그 다음 **`pytest`** 로 회귀 테스트(반드시 통과). 새 기능/버그수정엔 테스트를 함께 추가. 마지막에 `python run.py` 스모크.

**전 레이어 테스트 방법·릴리스 전 체크리스트는 [`TESTING.md`](TESTING.md) 가 단일 기록.**

## 7. .env 키 요약 (`.env.example` 복사)
- **MOLIT_SERVICE_KEY** = data.go.kr 키. 이 키 하나로 실거래+청약홈+HF+서민금융 공통(데이터셋별 활용신청).
- 지도/좌표: **NAVER_MAP_CLIENT_ID/SECRET**(우선) · **KAKAO_REST_API_KEY**(반경 POI).
- 뉴스: **NAVER_SEARCH_*** · 은행금리: **FINLIFE_API_KEY**.
- DB: **DATABASE_URL**(비우면 SQLite). 로그인: **KAKAO_LOGIN_REST_KEY / NAVER_LOGIN_***.
- 사진/운영: **STORAGE_***(local|s3) · **ADMIN_TOKEN** · **SCHEDULER_***.

## 8. 현재 상태 & 다음 작업
- **완료(요약)**: 실거래 파이프라인·대시보드·시세·추이·랭킹·단지상세·청약·뉴스·대출·세금·지도/히트맵·인근POI·개인화(계정 union)·소셜로그인(JWT)·사진 스토리지·매물 등록·통합검색·관리자/스케줄러·**커뮤니티 게시판(카테고리·이미지·@단지연결·대댓글·정렬·수정·좋아요·신고·베스트·내활동·스크랩·작성자 프로필)·알림**.
- **대규모 운영 개선**: ③원자카운터 ✅ · ②집계 캐시 ✅ · ⑤마이그레이션 일원화 ✅ · ⑥실거래 정정/해제 ✅ · ④검색 인덱스 ✅(pg_trgm GIN·0016·PostgreSQL) · ①프런트 빌드 ✅(Vite + PWA + **컷오버 확정**: 프로덕션 이미지가 dist 서빙, 단일 소스 / SEO 후속). 컨테이너 기동은 운영 머신 1회 검증.
- **모바일 앱(스토어)**: React Native 폐기 → **Capacitor 확정**(웹 단일 코드베이스). Phase A(Vite)·B(PWA) 완료, C(Capacitor 셸)~F(OTA·운영) 남음. SSOT: `MOBILE_APP_STRATEGY.md`.
- **중개사 대시보드(B2B v1)**: 계정 메뉴 → role=agent에게만 노출되는 `AgentDashboard` 시트(내 매물 요약 통계+관리·삭제·등록 진입·행 탭→상세). 조회수 추적(외부 조회만·소유자 제외)·상태관리(거래완료/숨김/복구)·매물 수정(PUT) 포함(v2). 리드/문의 추적은 미구현=v3.
- **수익화**: 전략 `MONETIZATION.md`. 부록B 스캐폴딩 존재(매물 `is_sponsored`/`priority`+"광고" 배지, `accounts.plan`+`is_premium` 게이팅, admin 테스트 엔드포인트) — **전부 피처 플래그(`feature_ads`/`feature_monetization`) 뒤·기본 OFF=현재와 동일**. 마이그레이션 0012.
- **배포/운영**: Dockerfile·`docker-compose.prod.yml`(web 다중워커+scheduler 단일+db)·CORS 환경변수화(`CORS_ORIGINS`, 기본 `*`)·`DEPLOY.md`(배포 전 점검·HTTPS·보안 체크) 준비됨. 컨테이너 실제 빌드·실행은 운영 머신 검증.
- **운영 준비(완료)**: 시세 **서버 집계**(price_overview) ✅ · **웹푸시**(VAPID·구독·발송·SW) ✅ · **모니터링**(JobRun·record_job·system_status·alert·Sentry·/admin/monitor) ✅ · **백업/복구**(pg_dump·restore·스케줄러) ✅ · **배포 자가진단**(scripts/doctor) ✅. 실서버에서 키 설정 + pytest + `doctor`로 최종 확인 필요.
- **차별화(완료)**: 생활권 점수 ✅ · 임장 도우미 ✅. **UI**: 모든 상세/검색 **바텀시트(SheetShell)+스와이프** 통일 ✅ · 청약 상세(마감 포함) ✅.
- 상세 체크박스·우선순위는 **`ROADMAP.md`** 가 SSOT. 작업할 때마다 갱신.

## 9. 상세 지침 — `skills/` (작업 전 먼저 읽기)
- `skills/README.md` — 원칙·레포지도·검증 총괄
- `skills/data-and-sources.md` — 수집·정규화·커넥터 방어 패턴(키/URL gating·tolerant·None)
- `skills/aggregations.md` — 집계 규칙(median·표본부족 None·gu_order·**stat_cached 캐시**)
- `skills/loan-costs.md` — LTV/DSR·세금·상품 카탈로그
- `skills/personalization.md` — 개인화(device_id→로그인 승계 union)
- `skills/auth-and-roles.md` — 소셜로그인·역할(user/agent)
- `skills/community.md` — 게시판·댓글/대댓글·좋아요/신고·알림·스크랩·작성자·**원자 카운터·포커스 규칙**
- `skills/deploy-and-db.md` — SQLite↔PostgreSQL·Alembic(0001~0011)·**웹푸시·모니터링·백업·doctor**·레이트리밋
- `skills/frontend.md` — UI 컨벤션·**SheetShell 바텀시트/스와이프 통일**·시세 드릴다운·상세 위젯·임장·푸시토글·데모폴백
- `skills/testing.md` — 테스트·CI(pytest·격리·픽스처)
- 외부 API 주소는 전부 config(.env 오버라이드, 빈 값이면 코드 기본값). 새 외부호출 추가 시 URL을 config 필드로 두고 `s.<field> or 상수` 패턴 사용.
- 버전 관리: 전달(배포)할 때마다 VERSION·CHANGELOG.md 갱신 후 산출물 파일명에 `_vMAJOR_MINOR` 접미사(예: cheongju-realestate_v1_1.zip / cheongju-ui_v1_1.html). 기능추가=MINOR, 구조/대변경=MAJOR.
- 운영 가이드: OPERATIONS.md(설치·운영·배포·모니터링·장애대응). 운영 관련 변경 시 함께 갱신.
- 정정/해제(⑥): collect.upsert_transactions(정정 갱신·해제 표시·모호 보존). 건수는 last_collect/status로 노출.
- 학군: api/complex._school_summary(카카오 POI 학교, 거리 기준·학업성취 아님). 공시가격: services/gongsi.py(공식 CSV 중앙값, 매칭실패 null).
- 단지 보강: app/sources/kapt/(client+normalize), app/services/enrich.py. 엔드포인트=config(KAPT_*_URL), 필드는 후보매핑(추측 금지·Swagger 확정). 미설정/미매칭=무보강(null). 상세 complex_meta.
- 법적 고지: 문서는 app/web/legal/*.md, 제공/동의는 app/api/legal.py. **정책 문구 변경 시 legal.py PRIVACY_VERSION/TERMS_VERSION 을 올려 동의 재수집**. 동의 이력=Consent.
- 레이트리밋: 새 쓰기성/공개 엔드포인트는 main.py `_rl_rule`에 버킷 추가 고려(app/core/ratelimit.py). 한도는 config.
- 관측성: `/health`(db_ok·신선도), `/status/data`(공개 집계). 운영 상태는 `app_meta`+`app/services/appmeta.py`.
- `skills/testing.md` — 테스트·CI(격리 원칙·픽스처·무엇을 테스트하나)
- `skills/deploy-and-db.md` — SQLite↔PostgreSQL·**Alembic 마이그레이션 일원화**·배포
- `skills/frontend.md` — UI 컨벤션·함정

## 10. 자주 실수하는 함정 (DO NOT)
- ❌ **JSX 렌더 루프에서 React 컴포넌트를 정의해 `<Comp/>`로 쓰지 말 것** → 매 렌더 리마운트로 **입력 포커스 빠짐**. 컴포넌트는 모듈 레벨에 정의. 리스트 항목에 인라인이 필요하면 **컴포넌트가 아니라 "JSX를 반환하는 렌더 함수"**(예: `renderCmt(c)`)로 작성(리마운트 없음).
- ❌ 외부 API 응답 필드 추측·0으로 채우기 금지 → tolerant 매핑 + None.
- ❌ 새 외부 커넥터에 `@ttl_cached` 누락 금지. 새 무거운 집계에 `@stat_cached` 누락 금지.
- ❌ **카운터를 `x = (x or 0)+1`로 갱신 금지** → 원자 `update(...).values(...)`.
- ❌ 운영 스키마 변경을 `create_all`에 의존 금지 → Alembic 마이그레이션 + `db_upgrade`.
- ❌ 숫자/가격 줄바꿈·정렬 깨짐 — `.num{white-space:nowrap}`, 가격칸 `flex:none`, 가변영역 `minWidth:0`+ellipsis.
- ❌ MOLIT 실거래를 특정 중개업소와 연결 금지(실거래엔 중개업소 없음). 인근 중개업소는 '참고'로만.
- ❌ 구별 섹션 정렬 제각각 금지 → `gu_order` 단일 기준.
