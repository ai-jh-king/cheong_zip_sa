# ROADMAP — 청주 부동산 플랫폼

진행 상황과 남은 작업을 한곳에서 추적합니다. (왜곡 없음 원칙은 전 항목 공통)

---

> 📢 2026-06-28: 웹 Claude → **Claude Code** 로 인수인계. 새 세션은 `HANDOFF_TO_CLAUDE_CODE.md` 를 먼저 읽을 것.

## 📌 현재 상태 스냅샷 (v1.176 · 인수인계용 요약)

**메인 기능(결정)**: '판단이 얹힌 지도' — 전체화면 지도 + 우리만의 시그널 핀(📉급매·🏗호재·현위치). 상세 CLAUDE 8.0.

**한 줄**: 청주 4개 구 실거래·시세·지도·청약·대출·커뮤니티가 라이브 작동. 청주 특화(호재·직주근접·육아·전세가율·가격검증) + 우리집/개인화 + 전입자 온보딩 완비. **앱 실구동 테스트로 검증됨**(pytest 147 + e2e 17). 남은 결정타는 코드가 아니라 **①운영 PostgreSQL 전환(데이터 영속) ②실사용 검증 ③시설 데이터 적재**.

**작동(데이터 있음)**: 실거래 시세·추이(1·3·5년 토글)·랭킹, 지도(마커·전체화면), 단지 상세(면적 병합·거래활발·전세가율 신호·직주근접·인프라·호가검증·단지이야기), 우리집(시세변동·서버동기화), 관심단지 시세, 청약, 대출/세금, 게시판(주민 뱃지), 온보딩, 급매 레이더.

**구조만 완성(데이터 대기)**: 🧸 육아·초품아·지도 POI → 시설 데이터 적재(NEIS 학원 키 + data.go.kr URL) = 최우선 남은 데이터 과제. 호재·통근거점은 seed 1회면 활성(데이터 준비됨).

**검증 체계(3층, 모두 실행 확인)**: ①`verify_all`(정적: 문법·import/속성 심볼·프런트) ②`pytest`(147) ③`smoke_e2e`(실제 HTTP 17여정). 전달 전 필수.

**알려진 부채**: ①운영이 SQLite면 재배포 시 데이터 소실 → **PostgreSQL 필수**(OPERATIONS 7). ②`frontend/src/main.jsx` 4,751줄 단일 파일 → 사용자 늘기 전 분리 권장. ③프런트 GU_NAME/GU_NAMES 중복 정의(충청 확장 시 통합).

**다음 우선순위**: 1)PostgreSQL 전환+데이터 확인 2)시설 데이터 적재(육아 활성) 3)지인 소프트런칭·실사용 검증 4)main.jsx 분리 5)알림 고도화 6)충북 확장. ✅공유 바이럴 장치 완료(카드 워터마크·호가검증 공유·친구 알리기, v1.170). **앱 배포**: PWA(오늘 가능)→Capacitor 스토어(설정 완료, MOBILE_DEPLOY.md).

**릴리스 규율**: 변경 시 `verify_all` PASS + `pytest` + `smoke_e2e` → `VERSION`/`CHANGELOG` 갱신 → zip 최상위 `cheong_zip_sa`. 배포 전 브라우저 스모크(TESTING).
---

## ✅ 완료
- **청주 특화·개인화·UI (v1.135~v1.152)**:
  - 청주 특화: 전세가율/역전세 신호(RentSignal — 갭 크기·주의점, 단정 없음), 개발 호재(홈 카드 CityIssues + 지도 핀, seed_landmarks), 직주근접(단지상세 hub_access, seed_commute), 육아(KidsEnv·초품아 배지, 시설데이터 대기).
  - 가격 검증 3종: 호가 검증(단지상세)·구 시세 맥락(분양)·급매 레이더(홈) — '말릴 수 있는 앱' 창끝, 판정 없음+면책.
  - 전략/온보딩: **전입자 온보딩 추천 백엔드**(/onboarding options·recommend — 직장근처+시세+예산차액 조립, 왜곡 없음·고지). 프런트 위저드 완료(전체화면 4단계·첫방문 자동안내·홈배너).
  - 커뮤니티: **단지 주민 뱃지 + 단지 이야기**(서버 대조 resident, complex 필터, ComplexTalk) — 아파트 인증 소통 MVP.
  - 개인화: 우리집 등록(MyHomeCard, UserPref.my_home 서버동기화), 관심 단지 시세(배치 /complex/quotes), 더보기=마이페이지.
  - **지침서 2.3 완비**: 단지 시세 시계열 **1·3·5년·전체 토글**(TrendBlock) + **거래량 추이 막대** + 전월/전년 동월 등락 표시(전체 이력 timeseries 기반). 전세가율(갭)=RentSignal.
  - 정보: 면적 평형 병합(23.1·23.2→23평), 단지상세 재배치(거래활발·지도·인프라 상단), 학군→인프라 통합.
  - 지도: 전체화면 레이아웃 + 필터/요약 오버레이, 총액(억) 마커·말풍선·클러스터, 시설 POI 토글(데이터 대기).
  - UI: 토스식 토글(선택만 은은)·공용 `.btn-primary` 버튼 클래스·다크모드 색 정리·스켈레톤 로딩·진입 캐시 워밍업.
  - 시세 탭·홈 시세 히어로는 숨김(검색·단지상세가 대체, 코드 보존).
- **M1 데이터 파이프라인** — 4개 구 실거래가 8종 수집·정규화·캐싱·dedup, 지역코드 검증, 인코딩/디코딩 키 자동보정·401 진단.
- **M2 시세/지표 + UI**
  - 집계: 평균, 전월/전년 등락, 전세가율, 추이 (표본 없으면 null).
  - **평단가(만원/평) 중앙값**(면적대별), 거래량, **신고가**, 가격변동 랭킹.
  - 랭킹: 매매가순/평단가순/등락/신고가/거래활발구 (셀렉트박스).
  - UI: 하단 3탭(홈 피드 · 랭킹+지도 · 시세), 한 번 실행(`python run.py`).
  - **지도**: 랭킹 단지 위치(카카오맵). 좌표는 `python -m scripts.geocode` 로 캐싱.
  - 시세 검색: 구·유형·거래·**선호 평형대** 필터 + 평단가 열.

## 지도 주기능화 (진행 — 호갱노노/아실 벤치마킹)
- [x] **1단계: 지도 전용 탭(하단 6번째) + 가격 마커**. 단지별 대표가(매매=평단가·전세/월세=보증금 중앙값) 색 마커, 거래유형·주택유형 필터, 마커 클릭→단지 상세. 좌표 미확인 단지 제외(왜곡 방지). 백엔드 `stats.map_markers`+`/map/markers`. (네이버 SDK 렌더는 운영 키로 시각 확인 필요)
- [x] 2단계: **뷰포트 "이 지역 평균" 패널 + 줌 기반 그리드 클러스터링**(줌아웃=묶음/곳 수, 줌인=개별 단지). 청주 규모라 마커는 1회 로드 후 뷰포트 요약·클러스터링을 클라이언트에서 처리(패닝마다 호출 없음). 백엔드 `map_markers`에 전체 summary 추가. (서버 bbox 로딩은 전국 확장 시 도입)
- [~] 3단계: **지도 영역 단지 목록 시트 + 다중선택 비교** 완료(보이는 영역 단지를 가격/이름순 목록으로, ⊕로 비교함에 담아 기존 비교 트레이→`/compare` 재사용). 구·동 경계 폴리곤·freehand 영역 그리기는 **데이터/SDK 의존으로 보류**(행정구역 GeoJSON·네이버 drawing 모듈 필요). 좌표 기반 뷰포트 영역 목록이 실질적 대체.

## 출시 품질 · 수익화 토대 (완료, v1.65~v1.94)
- **Vite 컷오버 구성**: `frontend/src/main.jsx` 정본화, 레거시 `app/web` 동결, Dockerfile 멀티스테이지(`WEB_DIR=dist`·SPA_MODE). 운영 빌드 검증만 운영자 몫.
- **PWA**: 설치형 + 오프라인 폴백(`offline.html`) + **앱 셸 런타임 캐싱**(navigate 네트워크우선 / 정적자산 캐시우선+SWR / **API 미캐시**) + 업데이트 배너. 배포 시 `sw.js`의 VERSION을 올리는 규칙(캐시 정리+배너 발화).
- **접근성**: `focus-visible`·reduced-motion, 클릭 요소 전체 키보드화(role/tabIndex/onKeyDown), 폼 라벨 연결(`LField`→`<label>`)·아이콘 버튼 aria-label·슬라이더 라벨. 색 대비 AA 확인.
- **긴 목록 페이지네이션**: 매물 서버 페이지네이션 + 청약·단지상세·시세(거래그룹·단지목록·검색결과) 더보기.
- **매물·중개사**: 매물 등록/수정/상태(거래완료·숨김)·조회수, **중개사 대시보드 v2**(내 매물·조회수·상태·수정).
- **출시 도구**: `scripts/preflight.py`(노출 안전성 점검), `store/`(스토어 메타 템플릿), `LAUNCH.md`(GTM 단계).

## 정보 고도화 (벤치마킹 기반)
- [x] **세금·총비용 계산기**(토스류): 취득세(1~3% 선형·생애최초 감면·농특세)·지방교육세·중개보수(상한)·법무 추정 → 대출과 합산해 **"이 집 총 필요현금"**. 법정요율 설정값 분리, 세무자문 아님 고지.
- [x] **평단가 히트맵 지도**(호갱노노): 단지별 평단가 중앙값을 색 핀으로(네이버 지도). ‘지도’ 탭, 핀 클릭→단지 상세. 좌표 없으면 제외(왜곡 방지).
- [x] **인근 인프라 POI**(호갱노노/직방): 단지 상세에 학교·지하철·마트·병원(카카오 카테고리검색, 거리순). KAKAO_REST_API_KEY 재사용(추가 키 X).
- [ ] 학군 상세(학업성취/배정학교, 학교알리미) — 후속(논쟁 소지로 신중).
- [x] **보유 데이터 분석 보강**: 단지 상세에 전세가율(갭)·전저점 대비·가격대·층별 평단가 추가, 랭킹에 신저가 추가. (키 0)
- [x] 홈 대시보드(전체 추이·구별 매매 랭킹·구별 최신거래+신고가·거래량)·소식 탭 분리·㎡/평 토글·랭킹 평형대 필터.
- [x] 가격 분포 히스토그램(시세 탭, 필터연동·중앙값/사분위·표본부족 처리, `price_distribution`+`/dashboard/distribution`).
- [ ] 전월세 전환율(추가 보강).

## 🔜 남은 작업 (우선순위 제안)

### M3 — 단지 상세 (데이터: 보유 + 지도/POI 키)
- [x] 랭킹/시세 항목 클릭 → 단지 상세: 시세 시계열, 면적별 평단가(중앙값), 전고점 대비, 거래량, 위치 지도, 최근 실거래.
- [ ] 지도에 인근 학교·지하철/버스·마트·병원 POI(네이버/카카오 장소검색). 키 필요.
- [ ] 단지×평형 단위 전세가율(갭).

### M4 — 청약 / 뉴스·정책 / 대출 추천 (외부 API 신규 연동 필요)
- [x] **청약·분양 실연동 커넥터**: 청약홈 API(data.go.kr 15098547) → 청주 공고 필터. 키 있으면 실데이터, 없으면 예시 폴백. (분양가는 주택형별 API 필요 → 후속)
- [x] **뉴스 실연동 커넥터**: 네이버 뉴스 API "청주 부동산"(제목·짧은요약·링크만, 원문 전재 금지). 키 있으면 실데이터, 없으면 예시 폴백.
- [ ] 정책·지원 큐레이션(현재 예시 유지).
- [x] 청약 경쟁률·당첨가점 + 주택형별 분양가/공급세대 보강(SubCard·attach_competition·`APPLYHOME_COMPETITION_URL`).
- [x] **대출 추천(핵심 차별화)**: 동의 화면 → 정보입력 → LTV·DSR min 한도 → 상품비교 → 월상환 시뮬.
      개인정보 미저장(stateless)·간이모드 폴백·금융조언 아님 고지 구현. (상품 금리는 finlife/HF 연동 전 예시)
  - [x] finlife 은행 주택담보대출 **실금리 연동**(공시 기준일 표기). 키 있으면 실시간, 없으면 예시 폴백.
  - [x] 은행 전세자금대출(finlife RENT) 병합 + 서민금융 '한눈에' 커넥터(`SEOMIN_API_URL` 설정 시).
  - [x] 정책대출(디딤돌·보금자리) HF 커넥터(app/sources/hf.py) — 검증된 HF 오픈API URL 설정 시 실연동, 미설정 시 예시. (data.go.kr 키 재사용)

## 개인화 (User Personalization)
- [x] **1단계(기기 기반·키 0)**: 표시 설정(㎡/평·내 동네) 저장, 최근 본 단지, 내 동네 우선 정렬·하이라이트. (`/me/prefs`, `/me/recent`, UserPref/RecentView)
- [~] 2단계: 대출 프로필 저장(기기 로컬·동의) ✅ · 맞춤 추천(관심·내 동네 기반) ✅ · 소셜 로그인(카카오/네이버) **구조 스캐폴드**(키 설정 시 OAuth 구현) · device→account 머지(예정).
- [x] 저장된 검색(시세 필터 저장·적용·삭제). (`/me/searches`, SavedSearch)
- [x] 관심 지역(구) 즐겨찾기 — 구별 랭킹 ★, 홈 '관심 지역' 섹션(클릭→시세). (Favorite target_type=region)

### M5 — 관심/알림 + 앱 패키징
- [x] **관심 단지 즐겨찾기**(키 0): 단지 상세 ★ 토글, 홈 ‘관심 단지’ 목록. 익명 device_id 기준 서버 저장(개인정보 없음), 미리보기는 메모리 폴백.
- [~] 알림: **푸시(웹푸시/VAPID) ✅**(관심 단지 신규 실거래·신고가 트리거, 알림함 PushToggle·SW·/push/*) · 이메일·카카오 알림톡은 채널 키 필요(예정).
- [~] 네이티브 앱(스토어): **React Native 폐기 → Capacitor 확정**(웹 단일 코드베이스 래핑, 장기운영 1코드베이스). Phase A(Vite 빌드)·B(설치형 PWA) **완료**, C(Capacitor 셸·Android 먼저)~D(네이티브 푸시+iOS)~E(스토어 심사)~F(OTA·운영) 남음. 상세·단계는 `MOBILE_APP_STRATEGY.md`.

## 부록 — 후행 확장(구조만 준비, 현재 OFF)
- [x] 수익화 스캐폴딩(전부 플래그 OFF=동작 불변): feature flags(ads/monetization), `Listing.is_sponsored/priority`·`Account.plan`, `entitlement.py`, 관리자 테스트 엔드포인트. 전략=`MONETIZATION.md`. **문의·리드(Inquiry) ✅**(매물 문의→중개사 대시보드 리드, 동의·소유자 한정). **결제/구독 스캐폴딩 ✅**(feature_billing OFF 기본·mock provider·구독 모델·리드 연락처 Pro 게이트·toss/portone 스텁). 다음: 실 PG 키 연동·웹훅 검증.
- [ ] 장단점 큐레이션 `InsightProvider` 교체형 모듈.
- [ ] 충북 전역/신규 유형 확장은 설정·코드값 추가만으로.

> 진행 방식: M4의 청약/뉴스/대출은 각각 외부 API·동의/개인정보 요건이 커서
> **항목별로 나눠 신중히** 구현합니다(한 번에 묶지 않음). 다음 작업은 협의 후 착수.

## 프로덕션 준비(대규모 서비스)
- [x] 1. 외부호출 캐싱 레이어(TTL·single-flight·negative). `app/core/cache.py`
- [x] 2. PostgreSQL 전환 + Alembic — URL 정규화(psycopg3)·커넥션풀·alembic 스캐폴드·docker-compose. 로컬 SQLite 폴백 유지.
- [x] 3. 프런트 빌드 파이프라인(Vite) — Phase A·B + **컷오버 확정**: 멀티스테이지 Dockerfile이 프런트 빌드→dist 서빙(`WEB_DIR` 고정), 소스 단일화(`frontend/src`). 레거시 동결. 컨테이너 기동은 운영 머신 1회 검증. (`CUTOVER.md`)
- [~] 4. 컨테이너·프로세스매니저·**Dockerfile ✅·docker-compose.prod(web 다중워커+scheduler 단일+db) ✅·CORS 환경변수화 ✅·DEPLOY.md ✅·스케줄러 ✅·모니터링 ✅·백업 ✅·배포 자가진단 ✅** · CI ✅(ci.yml). 컨테이너 실제 빌드·실행은 운영 머신 검증.

## 매물(등록 매물 · UGC) — 신규
- `Listing` 모델 + `/listings` API(등록/목록/상세/삭제) + Alembic 0001 + run.py 예시 시드(is_sample).
- 「중개대상물 표시·광고 명시사항」 기준 폼(거래형태·종류·소재지·면적·층·방향·방/욕실·관리비·입주가능일·준공일·가격·사진·중개업체 명시사항).
- 프런트 `매물` 탭: 목록(필터)·등록폼(사진 업로드)·상세(갤러리·전화문의). 실거래와 분리 표기 + 허위매물 고지.
- TODO: 사진 외부 스토리지(S3), 지오코딩 좌표·지도, 신고/검수, 로그인 연동 권한.


## 대중화 우선순위(확정)
P0 핵심 탐색: (1)통합검색 ✅완료 (2)지도 마커 탐색 (3)로그인 시 익명데이터→계정 이관
P1 재방문·신뢰: (4)알림(가격변동·신규매물·청약) (5)허위매물 신고·검수·거래완료 상태 (6)단지 리뷰/Q&A
P2 규모·운영: (7)SEO/PWA·동 드릴다운·공유 딥링크 (8)운영배포(Gunicorn·컨테이너·스케줄러·모니터링·CI)

### P0-1 통합검색 — 완료
- 백엔드 `GET /search?q=` → complexes(실거래 단지명, 대표 최근가)·regions(구+법정동)·listings(등록매물) 그룹.
- 프런트 SearchOverlay(디바운스 220ms) + 헤더 하단 검색박스 트리거. 결과 탭: 지역→구 시세, 단지→단지상세, 매물→매물상세 딥오픈(openId).
- 오프라인/미리보기: demoSearch 폴백(DEMO_TX/GU_NAME/DEMO_LISTINGS).

### P0-2 지도(부분) — 구 단위 마커 추가
- 지오코딩(카카오 키) 전에도 지도가 비지 않도록 **구 단위 집계 마커**(구 대표 좌표=근사 중심점) 추가. `stats.heatmap`가 districts(구별 평단가 중앙값+좌표) 동반 반환.
- 프런트 지도에 '구 단위/단지 단위' 토글(기본 구 단위). 구 핀 클릭→구 시세, 단지 핀(지오코딩 시)→단지 상세.
- 구 좌표는 region_codes.DISTRICT_CENTROIDS(근사, UI에 '구 평균/대표 위치' 명시 — 왜곡 방지). 단지 정밀 좌표는 scripts.geocode.

### P0-3 익명데이터 → 계정 이관 — 완료
- 방식: 스키마 최소 변경. 계정에 연결된 모든 device(DeviceLink)를 **union**해서 관심/최근/저장검색/표시설정을 cross-device로 통합.
- `auth.owner_device_ids(db, device_id, authorization)` 공통 헬퍼 → favorites·personal 읽기/삭제가 device 집합 기준.
- 매물은 로그인 시 `_adopt_device_data`로 익명 device 매물에 account_id 부여(내 매물에 합류).
- 프런트: 개인화 fetch 전반에 authHeader 부착 + account 변경 시 재조회(로그인/로그아웃 즉시 반영).
- 쓰기는 현재 device로, 삭제/조회는 계정 device 집합 기준(언팔도 여러 기기에 반영).

## P1 — 커뮤니티 게시판(부동산 소통) 추가
- 모델: Post/Comment/PostLike/ReportLog(신규 테이블, create_all 자동). 카테고리 자유/질문답변/정보공유/매물상담/지역소식.
- API `/community`: 목록(카테고리·지역·검색·정렬·페이지), 상세(+조회수), 작성/삭제(로그인), 댓글 추가/삭제, 좋아요 토글(중복방지), 신고(중복방지·임계치 자동숨김).
- 프런트 '게시판' 탭(7번째): 카테고리 칩·검색·정렬·더보기, 글 상세(본문·좋아요·신고·댓글), 글쓰기(로그인 게이트). 의견≠공식정보 고지.
- 매물 면적 단위(㎡↔평) 토글 누락 수정(카드/상세 fmtArea 적용), 매물 필터 한 줄 정리.
- 데모 폴백(DEMO_POSTS). (미사용 예시 시드 sample_posts/sample_listings는 v1.123에서 제거)

## 게시판 고도화 — 완료
- 이미지 첨부: Post.images(JSON), 업로드는 /listings/upload 재사용(스토리지 추상화). 카드 썸네일·상세 갤러리.
- @단지 연결: Post.complex_name/property_type/lawd_cd. 글쓰기 단지 검색 picker, 상세 ‘단지 시세 보기’→단지 상세.
- 베스트: /community/best(주간 like+comment 상위). 목록 상단 ‘이번 주 베스트’ 섹션.
- 내 활동: /community/mine(내 글·댓글). 게시판 ‘전체글/내 활동’ 탭. 목록 mine 필터.
- 신규 컬럼은 db.session._ensure_columns로 기존 테이블에 안전 추가(SQLite/PG ALTER, idempotent).

## 게시판 — 대댓글·정렬·수정 추가
- 대댓글: Comment.parent_id(1단계 평탄화). 답글 입력, 들여쓰기 표시.
- 댓글 정렬: 등록순/최신순(최상위 기준, 답글은 시간순).
- 글 수정: PUT /community/posts/{id}(작성자). PostForm 수정 겸용(프리필).
- 댓글 수정/삭제: PUT/DELETE /community/comments/{id}(작성자), 인라인 편집.
- 신규 컬럼(comments.parent_id)도 _ensure_columns로 안전 추가.

## 게시판 — 알림·스크랩·작성자 정보 (완료)
- 알림(Notification): 내 글 댓글 / 내 댓글 답글 시 생성(본인·중복 제외). 헤더 🔔+미읽음 배지, 알림 패널(열면 일괄 읽음), 클릭→해당 글. 인덱스(account_id,created_at)/(account_id,is_read). 현재는 폴링(unread_count).
- 스크랩(Bookmark): 글 상세 북마크 토글, 게시판 '스크랩' 탭. owner=acct:<id>|device, uq(owner,post_id). 목록은 스크랩 순서 유지.
- 작성자(AuthorView): 닉네임 클릭→작성자 글/배지/통계(/community/authors/{id}). 배지=글 수 기준(새내기/회원/활발/베테랑).
- 확장성: 신규 테이블 create_all 자동 생성, 인덱스/유니크로 중복·조회 최적화, N+1 회피(작성자/스크랩 단일 쿼리), denormalized message로 알림 조인 불필요.
- 향후: 실시간 알림(SSE/WebSocket/푸시)로 폴링 대체, 알림 타입 확대(좋아요/멘션), 작성자 팔로우.

## 확장성 개선 (6대 구조 항목)
순서: ③원자카운터 → ②시세 사전집계·캐시 → ⑤마이그레이션 일원화 → ⑥실거래 정정/해제 → ④검색 인덱스 → ①프런트 빌드/SEO.
- [완료] ③ 원자적 카운터: 조회수·댓글수·좋아요·신고수를 read-modify-write → SQL `UPDATE ... SET x = coalesce(x,0)±1`(좋아요 감소는 case로 0 하한). 동시 요청 lost-update/행잠금 경합 제거. like_count·report_count는 갱신 후 재조회로 정확값 반환.
- [완료] ② 시세 집계 캐시(데이터 버전 기반): stats 20개 함수에 @stat_cached. 같은 데이터 버전 안에서 집계 1회 계산→이후 캐시 제공(매 요청 전체 스캔+Python median 제거). 키에 data_version 포함, 수집/지오코딩 시 bump_data_version()으로 즉시 무효화. single-flight로 스탬피드 방지, 반환 deepcopy로 변형 안전, TTL 600s 백스톱. 출력 형식·수치 불변. (다음 심화 여지: PriceStat 영구 사전집계 테이블·Redis 공유 캐시·LRU 상한)
- [완료] ⑤ 마이그레이션 일원화: 베이스라인 0002_baseline 추가(Base.metadata 에서 전체 생성, checkfirst 멱등) → alembic 이 권위 소스. scripts/db_upgrade.py(설정 URL 기반 upgrade/stamp/current/history). 운영=alembic upgrade head, dev=create_all(스키마 동일). 기존 create_all DB 도 upgrade head 멱등 안전 / stamp head 로 편입. env.py target_metadata=Base.metadata 로 이후 autogenerate 지원.
- [완료] ⑥ 실거래 정정·해제 반영: 해제여부/해제사유발생일 파싱(is_canceled/canceled_date), identity_key(금액 제외)로 정정·해제 매칭. upsert v2 = 해제표시/정정갱신/멱등skip/신규. 집계·검색에서 isnot(True)로 해제 제외(NULL 안전). backfill_identity_keys로 기존행 매칭 활성화. 변경 시 캐시 버전 bump. 스키마 0003_tx_cancel.
- [x] ④ 검색 **pg_trgm GIN 인덱스**(0016, PostgreSQL) — `complex_name/dong_name/title LIKE '%q%'`(선두 와일드카드)를 인덱스로 가속(코드 변경 없이). SQLite는 스캔 폴백. (형태소 FTS는 후속 옵션)
- [x] ① 프런트 Vite **정본화**(`frontend/src/main.jsx`) + 설치형 PWA + 컷오버 구성(Dockerfile 멀티스테이지·`WEB_DIR=dist`). 운영 빌드 검증만 운영자 몫. SSR/SEO는 후속.

## 운영 토대 — 테스트 + CI (완료, 1차)
- pytest 스위트: 대출/세금(순수)·정규화 키(정정·해제 토대)·stat_cached 캐시·시세 집계(해제 제외)·커뮤니티 원자 카운터·API 스모크.
- conftest: 버리는 SQLite 강제 + 외부키 비움(네트워크 차단) + 테이블 격리.
- GitHub Actions CI(.github/workflows/ci.yml): compile 체크 + pytest (push/PR).
- 다음(2차): 시세 추이/대출 상품필터/지오코딩(모킹) 커버리지 확대, 커버리지 측정, ruff 린트.
## Tier2 — 관심 단지 신규 실거래 알림 (완료)
- services/notify_transactions.py: 수집(live) 직후 커서(app_meta.notify_last_tx_id) 이후 신규 실거래를
  관심 Favorite(단지=name__lawd__type, 지역=region:구명)과 집합 매칭 → DeviceLink 로 연결된 account 에
  Notification(type="transaction") 생성. 대상별 1건 그룹화, 모의/해제분 제외, 중복방지(커서).
- Notification 에 complex_name/lawd_cd/property_type 추가(클릭 시 단지 상세 이동). 알림 목록 응답에 포함.
- 마이그레이션 0003_tx_alerts(컬럼 + app_meta), _ensure_columns 안전망. 프런트 NotificationsOverlay 가
  transaction 타입은 단지 상세로 이동.
- 테스트 test_notify.py: 매칭·그룹화·커서 중복방지·모의/해제 제외·비로그인 제외.
- 한계/다음: 비로그인은 알림 미수신(로그인 시 수신), 관심별 on/off 토글 미구현(전역), 지역 매칭은 구명 문자열 기준.

다음 추천 작업: Tier1 잔여(관측성·레이트리밋) 또는 Tier2 단지 데이터 보강.

## Tier1 — 관측성·데이터 신선도 (완료)
- /health: DB 핑(db_ok)+data_version+last_collect_at. /status/data: 최신 계약일·구별 커버리지·수집 경과·stale·지오코딩 커버리지(공개 집계).
- app_meta 테이블 + app/services/appmeta.py(공용 메타). 수집 시 last_collect 기록. 알림 커서도 appmeta로 통일.
- 로깅: setup_logging(httpx 소음 억제)+요청 타이밍 미들웨어. UI 상단 '데이터 기준/갱신' 배너(+stale 경고).
- 테스트 test_ops.py. 다음: 레이트리밋·어뷰징 방어 → 개인정보처리방침/약관.

## Tier1 — 레이트리밋·어뷰징 방어 (완료)
- app/core/ratelimit.py(인프로세스 고정 윈도, 스레드안전, sweep) + main.py 미들웨어(_rl_rule).
- 분당 IP 한도: 로그인/글쓰기/댓글/신고/검색/매물등록(.env 조정, 0=무제한). 초과 429+Retry-After.
- 테스트 test_ratelimit.py(허용→차단·키분리·윈도리셋). 테스트는 RATE_LIMIT_ENABLED=false.
- 다음(Tier1 마무리): 개인정보처리방침·이용약관 페이지(대출 민감정보 동의 토대).

## Tier1 마무리 — 개인정보처리방침·이용약관 + 동의 이력 (완료)
- 문서: app/web/legal/privacy.md·terms.md(템플릿, 법무검토 고지 + [운영자 입력] 자리). 실제 처리에 정확히 일치:
  대출 민감정보는 서버 미저장(stateless), '저장' 선택 시 본인 브라우저에만 보관. 주민번호/계좌 미수집, 제3자 제공 없음.
- API app/api/legal.py: GET /legal/version·/legal/{doc}, POST /legal/consent(버전·시각 기록), GET /legal/consent/status.
  Consent 모델 + 마이그레이션 0004_consents. PRIVACY_VERSION/TERMS_VERSION 상수.
- 프런트: 푸터에 처리방침·약관 링크(LegalModal), ConsentGate에 '처리방침 보기' + 동의 시 POST /legal/consent 기록.
- 테스트 test_legal.py. ⚠️ 정책 문구 변경 시 legal.py 의 *_VERSION 을 올려 동의 이력을 새 버전으로 재수집할 것.

Tier1(토대) 4종 완료: 테스트+CI · 관측성 · 레이트리밋 · 처리방침/약관.
다음 추천: Tier2 — 단지 데이터 보강(세대수·공시가격·학군) 또는 6-fixes ⑥(실거래 정정·해제 반영).

## Tier2 — 단지 데이터 보강(공동주택 기본정보 K-apt) (완료, 1차)
- 소스: app/sources/kapt/(client+normalize). 흐름: 시군구→단지목록(kaptCode)→기본정보(세대수·동수·사용승인일→연식·난방·연면적·시공사·주차).
- 서비스 app/services/enrich.py: 실거래 등장 아파트만 대상, 이름 정규화 매칭(모호하면 건너뜀), 미설정/미매칭은 무보강(null 유지·날조 금지). last_enrich 메타.
- 실행: scripts/enrich.py / POST /admin/enrich. 엔드포인트는 config(KAPT_LIST_URL/KAPT_INFO_URL), 미설정 시 건너뜀.
- Complex 컬럼 추가 + 마이그레이션 0005. 단지 상세 응답에 complex_meta(없으면 null), 프런트 '단지 정보' 블록(출처 K-apt·아파트 한정·누락 미제공 표기).
- 테스트 test_enrich.py(문서 필드 매핑·누락 None·주차 합산). ⚠️ 실엔드포인트/필드는 Swagger 로 확정(코드는 후보매핑으로 관용).
- 다음: 공시가격·학군(정량) 보강, 또는 6-fixes ⑥(실거래 정정·해제 반영).

## 6-fixes ⑥ — 실거래 정정·해제 반영 (완료)
- upsert_transactions: 정정(동일 identity·금액변경→기존행 갱신, 중복금지)·해제(O→is_canceled, 집계제외)·멱등(dedup skip)·모호(active 2건+→신규 보존). backfill_identity_keys로 기존행 활성화. (로직은 기존 존재)
- 보강: 정정/해제 건수를 반환·last_collect·/status/data 로 노출. 회귀 테스트 test_corrections.py(멱등/정정/해제/모호).

## Tier2 — 공시가격·학군 보강 (완료)
- 학군(통학 접근성): 카카오 POI(학교 SC4) 실데이터로 인근 학교 수·최단·초/중/고 분류. /complex/detail school_access. '학업성취 아님·거리 기준' 명시. test_schools.py.
- 공시가격: 공식 CSV(호별) → 단지×면적 중앙값(원→만원) 집계 importer(app/services/gongsi.py, scripts/import_gongsi.py). 청주만·매칭실패 null. Complex 컬럼+마이그레이션 0006. complex_meta 노출. test_gongsi.py.
  ※ 깔끔한 단지단위 API 부재로 CSV 기반(운영자 제공). 헤더는 후보매핑.
- 운영 가이드 OPERATIONS.md 신설(설치·운영·배포·모니터링·장애대응·법무·점검 체크리스트).

## P1 — 단지 비교(Compare) (완료, v1.3)
- stats.compare_one + POST /compare(최대4). 프런트 상세 '비교' 토글·플로팅 바·오버레이(지표×단지, 최적 강조, safeStore 저장). 명세 2.5 충족.

## P1 — 청약·분양 정식 탭 (완료, v1.4)
- GET /subscription(청약홈, 예시 폴백). 전용 탭 SubscriptionTab(상태 필터·공고 카드·주택형별·출처 고지). 소식 탭은 뉴스·정책만. test_subscription.py.

## 차별화 — 예산 기반 단지 매칭 (완료, v1.5)
- loan.max_affordable_price + stats.affordable_complexes + POST /loan/affordable. 대출 화면 '내 예산으로 단지 찾기'. 대출+시세 결합. test_affordable.py.


## 운영 준비 · 차별화 · UI 통일 (완료, v1.50~v1.62)
- [x] **시세 서버 집계**(price_overview API·드릴다운, 클라이언트 500건 집계 대체) — v1.49~1.50
- [x] **생활권 점수**(POI 거리 기반·근거 공개·참고용) — v1.51
- [x] **UI 바텀시트 통일**(SheetShell): 단지·매물·게시판·청약·통근·예산·검색 + **아래로 스와이프 닫기**, 상세 뒤로버튼 제거 — v1.42~1.57
- [x] **청약 상세**(마감 공고도 결과 열람) — v1.56
- [x] **단지 상세 위젯**: 적정가 체크·거래 동향·외부 매물 링크·신고가 배지 — v1.45~1.48
- [x] **웹푸시**(VAPID·PushSubscription·/push/*·SW·PushToggle·notify 연계) — v1.58
- [x] **모니터링**(JobRun·monitoring 서비스·/admin/monitor·Sentry·경보 웹훅) — v1.59
- [x] **백업/복구**(scripts/backup·restore·스케줄러 연계) — v1.60
- [x] **임장 도우미**(TourSheet·체크리스트·메모 로컬저장) — v1.61
- [x] **배포 자가진단**(scripts/doctor) — v1.62
- [~] **공유·SEO 진입 페이지**(api/landing.py: /r/·/c/·sitemap·robots·OG 메타) — v1.65. (남음: og:image·SPA 딥링크)
- [ ] 후속 차별화 후보: 분양·청약 캘린더 · 내 단지 리포트(이메일/알림톡) · 하이퍼로컬 SEO 페이지
- [ ] 실서버 점검: 키 설정 → `python -m scripts.doctor` → `pytest` → 수집/푸시/백업 1회 실동작 확인

## 생활·교육·운동 인프라 (Place) — 차별화 (v1.113~)
- [x] 통합 `Place` 모델(교육/운동/생활 normalize) + 마이그레이션 0017 + source(public/claimed/ad) 자리.
- [x] 서비스/API(`/places/near`·`/region`·`/labels`) + 단지 상세 "주변 학원·운동·생활" 섹션.
- [x] 데이터 출처 명세 `DATA_PLACES.md`(학원·체육·도서관·의료 등 공공데이터 매핑·좌표계·갱신주기).
- [~] 수집기: 학원·**체육·의료** 구현(`academy`/`sports`/`medical` + 공통 `places_common.py`, tolerant 매핑). 도서관·어린이집까지 구현 완료(5종). 의료 EPSG:5174→WGS84(pyproj·범위검증·실패 시 좌표 None).
- [~] 가족 맞춤 점수: 엔진+API 구현(`fit_score`, /places/fit-score). 개인화 입력 UI·데이터 연결은 후속. / 청주 하이퍼로컬 심화 예정.
- [ ] (후행) 업체 직접 등록·홍보(source=claimed/ad) — 모델 자리 마련됨.

## 청주 개발 호재(Landmark) — v1.125~
- [x] 모델·마이그레이션·API·단지상세 섹션·시드 구조·왜곡방지 고지.
- [ ] 호재 데이터 큐레이션(출처·좌표와 함께 seed_landmarks 채우기).
- [ ] 지도 탭 호재 핀(데이터+화면 확인 후).
