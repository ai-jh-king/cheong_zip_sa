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
  sources/{applyhome,news,finlife,hf,seomin,kapt}.py  + places 계열 소스(academy/sports/medical/library/daycare)
  pipeline/collect.py    수집·정규화·dedup upsert·캐시 무효화
  services/{stats,loan,costs,geocode,poi,storage}.py
  services/{landmarks,commute,places,living,enrich,gongsi}.py  # 호재·통근/직주근접·시설·생활점수·단지보강·공시
  api/{dashboard,home,complex,loan,favorites,personal,   # 시세·대출·개인화
       auth,listings,search,admin,community,             # 로그인·매물·검색·관리자·게시판(+notif_router)
       landmarks,commute,places,legal}.py                # 호재·통근·시설·법적동의
  web/index.html         레거시 단일 React UI(동결·폴백)
  fixtures/              오프라인 검증 표본(is_sample)
frontend/                ★ 웹 정본(+ capacitor.config.json = 스토어 앱 설정, appId com.cheongzipsa.app). src/main.jsx = 단일 파일 React(현재 ~4,500줄, 100+ 컴포넌트) + PWA(manifest·아이콘·SW). build→dist(운영 서빙).
                         ⚠️ 단일 파일이 커서 블라인드 편집 위험 — 컴포넌트는 반드시 모듈 레벨(아래 10). 향후 파일 분리 권장.
scripts/                 run_collect / geocode / scheduler / db_upgrade / verify_region_codes / verify_frontend
                         seed_landmarks(호재) / seed_commute(통근거점·직주근접 공유) / collect_places(시설)
migrations/              Alembic (env.py가 앱 설정 URL 사용) — **head 0019**
skills/                  ★ 모듈별 상세지침(아래 9)
```

## 5. 데이터 모델
`Region` · `Complex` · `Transaction`(dedup_key 유니크·raw_payload 보존) · `Favorite` · `UserPref`(data JSON — **우리집 my_home 포함**) · `RecentView` · `SavedSearch` · `Account` · `DeviceLink` · `Listing` · `Post` · `Comment`(parent_id 대댓글) · `PostLike`(uq post+owner) · `ReportLog`(uq target+owner) · `Notification`(account_id 인덱스·type comment/reply/transaction/new_high) · `Bookmark`(uq owner+post) · `CommuteDestination`·`CommuteTime`(통근·**직주근접 hub_access 재사용**) · `PushSubscription`(웹푸시 구독·endpoint 유니크) · `JobRun`(배치 실행 이력) · `Landmark`(개발 호재 — category/status/lat/lng/summary/expected_year/source_*) · `Place`(생활·교육·운동 시설 — category/subcategory/lat/lng/source) · `Consent`(개인정보·약관 동의 이력·버전).
> **스키마 규칙**: 신규 컬럼은 ①모델에 추가 ②Alembic 마이그레이션 파일 생성(운영 PG) — SQLite 는 `_ensure_columns`(모델 자동 도출)가 시작 시 보강. 'no such column'은 대개 마이그레이션 미적용 or 운영이 SQLite. **마이그레이션 head = 0019**(…0018_landmarks → 0019_post_resident). 스키마 변경은 반드시 Alembic(아래 3).

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
**모든 수정 후(전달 전 필수)**: `python -m scripts.verify_all` — compileall+verify_imports(import/속성 심볼)+verify_frontend 단일 게이트. PASS 아니면 전달 금지. compileall만으로는 '존재하지 않는 심볼 import·def 유실 함수 흡수 → 런타임 부팅 실패'를 못 잡는다(실제 사고 AGG_MONTHS·complex_detail).
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
  - **프로덕션 안전 가드(v1.178)**: `app_env=production`이면 startup에서 **JWT_SECRET 미설정 시 부팅 거부**(다중 워커 임시키 불일치=간헐 로그아웃 예방), `AUTH_DEV_LOGIN=true`·CORS `*`는 경고. 판별=`Settings.is_production`.
  - **통근 거점 자동 시드(v1.178)**: startup에서 job 거점 0건이면 `seed_commute` 자동 실행(멱등·API키 불필요) → 전입자 온보딩(창끝) 부팅 직후 활성화. 플래그 `auto_seed_commute`(테스트는 false). 시드/시설 데이터 미적재 시 청주특화 기능 상당수가 '조용히 숨김'되므로 배포 체크리스트에 `seed_landmarks`·`seed_commute`·카카오 키를 필수화할 것.
- **운영 준비(완료)**: 시세 **서버 집계**(price_overview) ✅ · **웹푸시**(VAPID·구독·발송·SW) ✅ · **모니터링**(JobRun·record_job·system_status·alert·Sentry·/admin/monitor) ✅ · **백업/복구**(pg_dump·restore·스케줄러) ✅ · **배포 자가진단**(scripts/doctor) ✅. 실서버에서 키 설정 + pytest + `doctor`로 최종 확인 필요.
- **차별화(완료)**: 생활권 점수 ✅ · 임장 도우미 ✅. **UI**: 모든 상세/검색 **바텀시트(SheetShell)+스와이프** 통일 ✅ · 청약 상세(마감 포함) ✅.
- 상세 체크박스·우선순위는 **`ROADMAP.md`** 가 SSOT. 작업할 때마다 갱신.

### 8.0 제품 전략(포지셔닝) — 인수인계 핵심
- **메인 기능(결정) = '판단이 얹힌 지도'**: 유입·체류는 지도가 만들고(부동산 앱의 첫 본능), 차별화는 지도 위 시그널(📉급매 핀·🏗호재 핀, 향후 전세가율 위험)이 만든다. 지도는 전체화면+오버레이 필터+현위치. '가격만 찍힌 지도'가 아니라 말릴 수 있는 앱의 판단 재료를 지도에 올리는 것이 정체성.
- **해자 = 이해상충 없음**: 청집사는 중개·광고 수익이 0 → 대형 앱이 구조적으로 못 하는 '거래를 말리는 정보'(역전세 경고·과열 구간·대안 단지)를 전면에 낼 수 있다. 모든 신호는 참고·근거·면책(왜곡 없음)로 이 포지션을 지킨다.
- **창끝 = 전입자 온보딩**: SK하이닉스·오송·오창 발령자 등 '청주가 처음인' 신규 수요층에게 직장근처+시세+조심할점을 큐레이션. 기존 부품(통근검색·시세·전세가율) 조립.
- **복리 = 주민 인증 커뮤니티**(v1.158) 데이터 축적.

### 8.1 최근 추가(v1.135~v1.152) — 청주 특화 & 개인화 & UI
- **청주 특화 3축**:
  - **개발 호재**: 홈 '🏗 청주는 지금' 카드(`CityIssues`, GET `/landmarks`) + 지도 '🏗 호재' 토글 핀(클릭 시 요약·출처). 데이터=`scripts/seed_landmarks`(실제 출처: SK하이닉스 P&T7·오창 방사광가속기·테크노폴리스·북청주역세권·OSCO).
  - **직주근접**: 단지 상세 '🏭 직장·거점 거리'(`work_access`, `commute.hub_access` — CommuteDestination 좌표 재사용, **직선거리** 명시). 데이터=`scripts/seed_commute`(SK하이닉스 청주캠퍼스 포함).
  - **전세가율/역전세 신호**: 단지 상세 '전세가율' 카드(`RentSignal`, `stats.rent_gap_signal`) — 전세가율(전세중앙값/매매중앙값)을 갭 크기·주의점으로 해석. 청주 최대 화두(갭투자·역전세) 대응. **가격 예측·역전세 단정 금지**, 수치·근거·면책만.
  - **육아**: 단지 상세 '🧸 육아 환경'(`KidsEnv`, d.places 기반 어린이집·학원·소아과 등 개수) + '🏫 초품아/초등 도보권' 배지(school_access 재사용). **시설 데이터 적재 시 작동**(아래 8.2).
- **우리집(내 아파트)**: 홈 최상단 `MyHomeCard`(최근 매매가+전월/지역대비 변동%, GET `/complex/detail`). 등록=검색 오버레이 homePick 모드. 저장=`UserPref.data.my_home` → **로그인 시 기기 동기화**(비로그인=로컬 safeStore).
- **더보기 '🛡 전세 안전 진단'(JeonseGuard)**: 링크가 아닌 **앱 내 계산** — 매매시세·보증금·근저당 채권최고액(등기부 을구) 입력 → (보증금+선순위)÷시세 % 밴드(≥80 위험/70~80 주의/<70 여유) + 계산식·'채권최고액=원금 110~130%' 설명 + 단정 금지 면책. 접이식 계약 단계별 체크리스트(계약 전/계약일/잔금·입주 — 확정일자·전입신고·체납열람 등 검증 사실만, '법률 자문 아님' 고지). ⚠️ 단지 상세의 전세가율 게이지 `JeonseSafety({ratio,scope})`와 별개 컴포넌트(이름 충돌 사고→개명, verify_frontend에 중복 정의 검사 추가).
- **더보기 '계약 전 꼭 확인'(OfficialLinks)**: 앱이 대신 못 해주는 필수 확인을 공식 서비스로 연결 — 등기부등본(iros)·건축물대장(정부24)·실거래 원본(rt.molit)·공시가격(realtyprice)·전세보증/안심전세(HUG)·금리비교(금감원 finlife)·임대차신고(rtms.molit)·홈택스·청약홈·청주시청 — 총 10종. '말릴 수 있는 앱' 정체성(직접 확인 권유)+무관·무수익 고지. 링크는 공식 최상위 도메인만(경로 하드코딩 금지 — 개편에 강함).
- **유입(바이럴) 장치**: ①시세 공유 카드에 워터마크(청집사+접속 도메인 location.host — 카톡 확산→유입 연결) ②호가검증 결과 '📤 공유'(navigator.share→클립보드 폴백, 면책 포함 텍스트) ③더보기 '📣 친구에게 알리기'(중개·광고 없음 소개문). SEO 랜딩(/r·/c·sitemap)은 기구현.
- **가격 검증 3종(services/pricecheck + /pricecheck/*)**: ①호가 검증 `quote`(단지상세 PriceCheck 카드 — 중앙값 대비 %·이하거래 백분위) ②구 시세 맥락 `gu-context`(분양 탭 GuContextBar) ③급매 레이더 `bargains`(홈 BargainRadar + **지도 📉급매 토글 핀**(showBg, 좌표는 응답에 포함·미지오코딩 시 핀 제외) — 같은 평형 12개월 중앙값 대비 ≤-12% 실거래 사실, 표본≥4). 판정 금지·면책 필수. 집계 윈도우=settings.aggregate_months.
- **전입자 온보딩(전략 창끝)**: `services/onboarding.py`(+ `api/onboarding.py`, main 등록). `GET /onboarding/options`(직장·산단 = commute job 거점) · `GET /onboarding/recommend?dest_key=&budget=&has_kids=` — 직장 근처 단지(search_by_commute) + 최근가(complex_quotes) + 예산 **차액(over_budget_by, 판정 아님)** 조립. 새 데이터 생성 없음·고지 포함. 프런트 위저드 완료(`OnboardingWizard` — 전체화면 4단계: 직장→예산→가족→결과, 진행도트·큰 탭타겟·최신 트렌드). 첫 방문 1회 자동 안내(safeStore `cj_onb_seen`)+홈 배너+마이페이지 진입. 저장=UserPref.data.onboarding(로그인 동기화).
- **단지 인증 소통(주민 뱃지·단지 이야기)**: 글 작성 시 서버가 작성자 '우리집(prefs.my_home)'과 @단지 태그를 **대조**해 `Post.resident` 저장(자가 신고 아님·서류 인증도 아님 — '자가 등록 기반' 정직 라벨). 목록 `GET /community/posts?complex=` 필터. 프런트: PostCard/PostSheet 🏠주민 뱃지 + 단지 상세 `ComplexTalk`(단지 이야기 최근 5건). 후행: 관리자 서류 인증 승격 여지.
- **관심 단지 시세**: FavList가 `POST /complex/quotes`(배치, 1쿼리 N단지)로 최근가·전월대비 표시.
- **더보기=마이페이지**: 프로필+우리집+바로가기(관심/청약/게시판)+집찾기 도구.
- **시세 추이 차트(지침서 2.3)**: 단지 상세 `TrendBlock` — 1·3·5년·전체 토글(데이터 있는 옵션만), 가격 라인+거래량 막대(월별 count), 전월/전년 동월 등락 칩. timeseries(전체 이력) 재사용, 표본 적은 달 주의 문구.
- **면적 병합**: 단지 상세 면적별을 **평형(round(평)) 단위 병합**(stats.complex_detail; 23.1·23.2평→23평). 대표면적=중앙값.
- **지도 시설(POI) 레이어**: 지도 '🎓학원/🏃체육/🏪생활' 토글 + 확대(zoom≥15) 시 표출(GET `/places/map` bbox). **시설 데이터 대기**.
- **UI 정리**: 필터·토글은 토스식(선택만 은은, 초록채움·경계 제거) / **주요 버튼은 공통 `.btn-primary` 클래스**(테마대응·일관 반경12·active 피드백). 지도 **전체화면**(헤더48+네비60 기준 calc, 필터/요약 오버레이). 다크모드 하드코딩색 정리.

### 8.2 데이터 적재 상태 (중요 — 왜곡 없음: 미적재 기능은 '숨김')
| 데이터 | 상태 | 활성 기능 |
|---|---|---|
| 실거래(MOLIT) | ✅ 라이브(키 있음) | 시세·추이·랭킹·단지상세·우리집·관심시세·지도마커 |
| 지도(네이버) | ✅ 키 있음 | 지도 렌더 |
| 호재(seed_landmarks) | ⚠️ 시드 실행 필요 | 홈 개발이슈·지도 호재핀 |
| 통근거점(seed_commute) | ⚠️ 시드 실행 필요 | 직주근접(직장 거리) |
| 시설(collect_places+geocode places) | ❌ 미적재(NEIS·data.go.kr 키) | 육아환경·초품아·지도 POI |
> 적재 절차·명령은 `OPERATIONS.md`·`DATA_PLACES.md` 참조. 미적재 시 해당 UI는 렌더되지 않음(빈 화면 아님).

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
- ❌ **한 컴포넌트의 지역 헬퍼(예: 지역 `const segBtn`)를 다른 컴포넌트에서 쓰지 말 것** → 스코프 밖 `ReferenceError`로 **런타임 크래시**(실제 v1.136 게시판 크래시 원인). 공용 헬퍼는 **모듈 레벨**에 두거나(예: `guOf`·`onEnter`·`eok`·`Delta`) 인라인으로. 새 버튼은 공용 CSS 클래스 **`.btn-primary`/`.btn-ghost`**(index.html) 사용 권장.
- ⚠️ **소셜 로그인 URL 인코딩**: 카카오/네이버 OAuth `redirect_uri`·`state`는 `urllib.parse.quote(safe="")`로 인코딩 필수(콘솔 등록값과 문자 단위 일치 요구). 미인코딩 = KOE006·redirect_uri_mismatch(v1.175 수정). 트러블슈팅: `SOCIAL_LOGIN_DEBUG.md`.
- ⚠️ **React 훅 구조분해 누락**: 새 훅 사용 시 파일 상단 `const {...} = React;` 에 반드시 추가. 누락 시 오프라인 검사(괄호·구문)는 통과하지만 **런타임 ReferenceError로 해당 화면 크래시**(실제 사고: v1.169 지도탭 useRef 미포함). verify_frontend 에 정합 검사 추가.
- ⚠️ **`def` 줄 str_replace 시 데코레이터 전이 주의**: 데코레이터(`@stat_cached()` 등)가 붙은 함수의 `def` 줄을 교체·이동하면, 데코레이터는 제자리에 남아 **아래로 새로 온 함수에 잘못 적용**된다(실제 사고: rent_gap_signal 이 stat_cached 를 물려받아 인자 무관 첫 결과만 반환=전세가율 왜곡). `@stat_cached`는 `(db, ...)` 시그니처 전용(첫 인자를 db로 간주).
- ⚠️ **`def` 줄을 포함한 str_replace 주의**: 함수 시그니처를 교체할 때 새 내용에서 그 `def` 줄을 빠뜨리면, 뒤 본문이 **앞 함수에 흡수**돼(문법상 정상 → compileall 통과) 해당 함수가 **정의 소실**된다(실제 사고: complex_detail). 편집 후 `scripts/verify_imports`로 확인.
- ⚠️ **오프라인 검증(괄호·compileall·verify_frontend)은 런타임 ReferenceError를 못 잡는다.** 심볼이 실제 스코프에 있는지 눈으로 확인하고, 배포 전 브라우저 스모크(게시판 진입·지도·단지상세 열기)를 반드시 수행(`TESTING.md`).
- ❌ 외부 API 응답 필드 추측·0으로 채우기 금지 → tolerant 매핑 + None.
- ❌ 새 외부 커넥터에 `@ttl_cached` 누락 금지. 새 무거운 집계에 `@stat_cached` 누락 금지.
- ❌ **카운터를 `x = (x or 0)+1`로 갱신 금지** → 원자 `update(...).values(...)`.
- ❌ 운영 스키마 변경을 `create_all`에 의존 금지 → Alembic 마이그레이션 + `db_upgrade`.
- ❌ 숫자/가격 줄바꿈·정렬 깨짐 — `.num{white-space:nowrap}`, 가격칸 `flex:none`, 가변영역 `minWidth:0`+ellipsis.
- ❌ MOLIT 실거래를 특정 중개업소와 연결 금지(실거래엔 중개업소 없음). 인근 중개업소는 '참고'로만.
- ❌ 구별 섹션 정렬 제각각 금지 → `gu_order` 단일 기준.
