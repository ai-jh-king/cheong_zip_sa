# 변경 이력 (CHANGELOG)

> 버전 표기: `vMAJOR_MINOR` (파일명) / `MAJOR.MINOR` (VERSION). 배포(전달)할 때마다 한 칸 올립니다.
> 규칙: 큰 기능/구조 변경=MAJOR, 기능 추가·개선=MINOR. 각 항목은 사용자 관점으로 간결히.

## v1.109 (2026-06-28)
- **Render 배포 준비(웹/PWA 출시)**.
  - `render.yaml` 블루프린트 추가 — 한 번의 Apply로 ① 웹 서비스(Docker, /health, JWT/ADMIN 자동생성, AUTH_DEV_LOGIN=false, 배포 시 `db_upgrade` 자동) ② 관리형 PostgreSQL ③ 매일 실거래 수집 크론(04:00 KST)을 함께 생성. 비밀값(MOLIT_SERVICE_KEY·CORS_ORIGINS)은 sync:false로 대시보드 입력.
  - `DEPLOY.md`에 Render 단계별 가이드(푸시→블루프린트→비밀값→마이그레이션 자동→첫 수집→도메인→PWA) 추가.
  - 기존 Dockerfile이 그대로 호환(멀티스테이지: 프런트 빌드→백엔드에 dist+WEB_DIR, `${PORT}` 대응) — 코드 변경 없음.
## v1.108 (2026-06-26)
- **버그 수정: `compare_one` NameError** (테스트가 검출). `app/services/stats.py`의 `compare_one`에서 `trade_count`가 정의되지 않은 `trades_recent`를 참조 → 실제 변수 `trades`로 수정. `/compare`(단지 비교) 요청 시 항상 터지던 실버그(다른 함수의 변수명이 잘못 복붙된 오타). 다른 함수(630행)의 `trades_recent`는 정상.
  - `test_compare.py::test_compare_one_metrics`·`test_compare_api` 가 잡아낸 것 — 컴파일로는 안 잡히는 런타임 버그를 테스트가 검출(테스트 추가의 가치).
## v1.107 (2026-06-26)
- **테스트 실행 경로 수정**: `pytest.ini`에 `pythonpath = .` 추가 — `pytest -q` 가 프로젝트 루트를 sys.path에 넣어 `app` 패키지를 찾도록(이전엔 `ModuleNotFoundError: No module named 'app'`). pytest 7+/8 지원 옵션. (코드 변경 없음·설정 한 줄)
  - 우회법: `python -m pytest -q` 또는 `PYTHONPATH=.` 도 동일 효과.
## v1.106 (2026-06-26)
- **회원 탈퇴(계정 삭제) — 실서비스/스토어 필수 기능**.
  - `DELETE /auth/account`(로그인+confirm 필수, **원자적 한 트랜잭션**). 설계(개인정보보호법·전자상거래법 고려):
    - **삭제**: 계정·기기연결·개인화(관심/최근/저장검색/설정)·좋아요/스크랩/신고·알림·푸시·내 매물·문의(받은+보낸).
    - **익명화**: 내 게시글/댓글 → 작성자 식별 제거(‘탈퇴한 사용자’)·스레드 보존.
    - **보존**: 구독/결제 기록(법정 보존의무)·동의 이력(적법성 증빙). ⚠️ 실 PG 도입 시 결제기록 보존정책 재점검 필요.
  - 프런트: 계정 메뉴에 ‘회원 탈퇴’(확인 다이얼로그→삭제→로그아웃·새로고침).
  - 처리방침: 권리 섹션을 ‘앱 내 회원 탈퇴로 즉시 삭제·게시글 익명화·법정 보존 예외’로 보강(두 복사본 동기화, 같은 2026-06-26 버전 내 보강이라 추가 재동의 없음). 스토어 메타에 ‘계정 삭제 제공’ 요건 충족 표기.
  - 테스트: `tests/test_account_delete.py`(4) — 401·400(confirm)·cascade+익명화·탈퇴 후 토큰 무효. (총 106→110)
  - 검증: 백엔드·테스트 py_compile·compileall PASS, 프런트 verify_frontend·괄호 균형 PASS. ⚠️ pytest 실행은 머신에서.
  - 문서: DATA·TESTING(R)·privacy(2벌)·store.
## v1.105 (2026-06-26)
- **초기 로딩·전송 최적화**(번들에 무거운 라이브러리가 없어 핵심은 압축·캐시).
  - **gzip 압축 미들웨어**(`GZipMiddleware`, minimum_size=600): JS/CSS/HTML/JSON 전송량 약 65~70%↓.
  - **정적 캐시 헤더**: SPA 마운트를 `_CachedSPA`로 교체 — 해시 자산 `/assets/*`는 1년 `immutable`, 그 외(index/manifest/아이콘)는 `no-cache`. `index.html`·`sw.js` 라우트도 `no-cache` 명시(업데이트 즉시 반영).
  - **Vite manualChunks**: React vendor를 별도 청크로 분리(앱 코드 변경 시 React 청크 캐시 유지).
  - 판단 근거: 의존성이 react+react-dom뿐(차트=SVG·지도 SDK=외부) → 파일 분할/코드 스플리팅은 위험 대비 실익 적음. 압축·캐시가 실질 지렛대.
  - 검증: 백엔드 compileall·vite.config 문법 PASS. ⚠️ 실제 효과(전송량·캐시 적중)는 머신에서 `npm run build`+DevTools로 확인(샌드박스는 빌드 불가).
  - 문서: DEPLOY(초기 로딩·전송 최적화).
## v1.104 (2026-06-26)
- **고도화 #1 레이트리밋 + #3 매출기능 테스트**.
  - **#1 보안**: `POST /inquiries`(연락처 포함 PII)와 `/billing/*` 가 레이트리밋 분류에서 빠져 있던 것을 추가 — 버킷 `inquiry`(6/분)·`billing`(20/분), config·.env.example 반영. 문의 스팸/PII 오남용 차단.
  - **#3 테스트**: `tests/test_inquiry.py`(8)·`tests/test_billing.py`(7) 신규(총 91→106). 문의=동의 필수·소유자만 연락처·404·타인차단·상태변경 권한·summary·401; 결제=feature_billing OFF 불변식(plans/me disabled·checkout/confirm/cancel 404)·플랜 구조·mock 토큰.
  - 검증: 백엔드·테스트 py_compile PASS. ⚠️ 샌드박스에 pytest/sqlalchemy 미설치 → 테스트 **실행 불가**, 통과는 머신 `pytest -q` 확인 필요.
  - 문서: TESTING(Q)·.env.example.
## v1.103 (2026-06-26)
- **지도 코드 리뷰 + 실서비스 보강**(렌더 불가 환경이라 정독 리뷰로 검수).
  - ① `stats.map_markers`에 `@stat_cached()` 적용 — 주 기능 지도가 트래픽이 많은데 매 호출마다 `_load`+전체 Complex를 재계산하던 것을 캐시(거래유형·유형별 키, 수집/지오코딩 시 자동 무효화).
  - ② `PriceMarkerMap` 언마운트 정리 추가 — idle 리스너 제거·마커 정리(탭 이동 시 unmounted setState 경고·리스너 누수 방지).
  - 리뷰 결과: 핵심 로직(무한루프·stale 클로저·Naver API 사용·빈데이터/좌표없음 처리)은 이상 없음 확인. 남은 관찰: viewport 목록 상위 300 캡(패널 카운트는 실수치)·구동 폴리곤/그리기 미구현(데이터·SDK 의존)은 의도된 범위.
  - 검증: compileall·verify_frontend·괄호 균형 PASS.
## v1.102 (2026-06-26)
- **지도 3단계 — 영역 단지 목록 시트 + 다중선택 비교**(기존 비교 인프라 재사용).
  - `AreaListSheet`: 지도에 보이는 영역의 단지를 가격순/이름순 목록으로(단지명·구/동·건수·대표가). 행 탭→단지 상세, ⊕→비교함 담기(`inCompare`/`toggleCompare`, 최대 4개). 담으면 기존 하단 비교 트레이→`CompareOverlay`(`/compare`)로 연결.
  - `PriceMarkerMap`의 `onViewport`가 보이는 마커 목록(items, 상위 300)도 보고 → `MapHub` "목록" 버튼으로 시트 오픈. 백엔드 변경 없음(`/map/markers`·`/compare` 재사용).
  - 무한루프 없음(effect 의존성 안정). 검증: compileall·verify_frontend·괄호 균형 PASS.
  - 보류(정직): **구·동 경계 폴리곤·freehand 영역 그리기**는 행정구역 GeoJSON·네이버 drawing SDK 의존이라 미구현 — 좌표 기반 뷰포트 영역 목록이 실질 대체. (ROADMAP 3단계 [~])
  - 문서: ROADMAP·TESTING(P).
## v1.101 (2026-06-26)
- **지도 2단계 — 뷰포트 "이 지역 평균" 패널 + 줌 클러스터링**.
  - `PriceMarkerMap` 재작성: 지도 idle(0.35s 디바운스)마다 보이는 영역 기준으로 **그리드 클러스터링**(줌아웃=묶음 "N곳"+중앙값, 줌인=개별 단지) + **뷰포트 요약**(곳 수·중앙값) 콜백. 묶음 클릭=줌인, 개별 클릭=단지 상세. 필터 변경 시 1회 fitBounds(패닝과 충돌 방지).
  - `MapHub`에 "이 지역" 패널(보이는 영역 곳 수·중앙값; 매매=평단가, 전세/월세=보증금). 백엔드 `map_markers`에 전체 summary(count/median/avg) 추가.
  - 설계: 청주 규모상 마커 1회 로드 후 뷰포트 요약·클러스터링은 클라이언트 처리(패닝마다 네트워크 호출 없음 → 빠르고 견고). 서버 bbox 로딩은 전국 확장 시 도입.
  - 무한루프 방지: render effect 의존성(markers/onViewport 참조) 안정 확인. 검증: compileall·verify_frontend·괄호 균형 PASS. (지도 상호작용은 NAVER 키+좌표로 머신 확인 필요)
  - 문서: ROADMAP(2단계 완료)·TESTING(O). 다음: 3단계(구·동 폴리곤·영역 검색·지도 비교).
## v1.100 (2026-06-26)
- **지도 주기능화 — 1단계(지도 전용 탭 + 가격 마커)**. 경쟁사(호갱노노·아실)처럼 지도를 주 진입점으로.
  - 하단 네비 6번째 **"지도" 탭** 신설. `MapHub`(거래유형·주택유형 필터) + `PriceMarkerMap`(네이버 SDK, 단지별 대표가 색 마커·클릭→단지 상세).
  - 백엔드 `stats.map_markers`(거래유형별 중앙값: 매매=평단가, 전세/월세=보증금 + 좌표, 가격대 분위 bands) + `/map/markers` 라우터. 좌표 미확인 단지 제외(왜곡 방지).
  - 마커 색=가격대 분위(5단계), 매매 라벨=평단가(만원/평)·전세/월세=보증금(억). 최근 집계 윈도우 기준 참고용 고지.
  - nav는 flex:1이라 6탭 자동 분배(레이아웃 변경 없음). map 아이콘 기존 보유.
  - 검증: compileall·py_compile PASS, 프런트 괄호 균형·verify_frontend PASS. (지도 렌더·엔드포인트 실제 동작은 NAVER_MAP_CLIENT_ID+좌표로 머신 확인 필요 — 샌드박스 불가)
  - 문서: ROADMAP(지도 주기능화 1·2·3단계)·TESTING(N). 다음: 2단계 bbox 뷰포트·클러스터링.
## v1.99 (2026-06-26)
- **검색 인덱스 — pg_trgm GIN(확장성)**. 선두 와일드카드 `LIKE '%q%'` 풀스캔 개선.
  - 마이그레이션 `0016_search_trgm`(head): PostgreSQL에 `pg_trgm` 확장 + GIN 인덱스(`gin_trgm_ops`) 5개(transactions.complex_name/dong_name, listings.title/complex_name/dong_name). **dialect 가드**로 SQLite는 no-op(스캔 폴백). 멱등(IF NOT EXISTS). 기존 `.like()`를 코드 변경 없이 가속.
  - 정합화: CLAUDE.md가 ④를 ✅로 표기했으나 ROADMAP/README는 "예정"이던 **불일치 해소** — 실제 구현하며 셋 다 완료(pg_trgm·0016·PostgreSQL)로 통일.
  - 운영 주의(DEPLOY): 관리형 DB는 `CREATE EXTENSION` 권한 필요, 대형 테이블은 CONCURRENTLY 수동 생성 옵션, 트라이그램 3글자↑ 선택도. 검증법(EXPLAIN)은 TESTING.md M.
  - 검증: compileall PASS, 마이그레이션 head 단일(0016). (인덱스 사용 여부는 운영 PostgreSQL에서 EXPLAIN 확인 필요 — 샌드박스 불가)
## v1.98 (2026-06-26)
- **개인정보처리방침 보강(문의 연락처·결제 반영) — 초안**.
  - privacy.md 1항(수집): 매물 **문의 연락처·내용**(동의 시 입력, 등록자에게 전달)·**결제 식별값**(PG 처리, 카드/계좌 미저장) 추가. 로그인 항목 문구 정합.
  - 2항(목적): 문의 전달·응대, 구독 결제·권한 관리 추가. 3항(보유·파기): 문의·결제 보유/파기 항목 추가(`[운영자 입력]` 보유기간). 4항(제3자): **"제3자 제공 안 함"→문의 연락처는 매물 등록자에게, 결제정보는 PG에 전달**로 정정(실제 동작과 일치).
  - app/web/legal·frontend/public/legal 두 복사본 동기화. `PRIVACY_VERSION` 2026-06-19→**2026-06-26 상향(동의 재수집)**.
  - 스토어 라벨 템플릿(google-play·app-store)에 문의 연락처(제3자 공유)·결제 항목 반영 안내 추가.
  - ⚠️ **법무 검토 필수**(본 문서는 초안·법률 자문 아님). 재수집을 원치 않으면 PRIVACY_VERSION 한 줄 되돌리면 됨. `[운영자 입력]` 항목(보유기간·PG명·연락처) 확정 필요.
  - 검증: legal.py py_compile PASS, 두 복사본 동일.
## v1.97 (2026-06-25)
- **결제/구독 스캐폴딩(첫 매출) — 전부 `feature_billing` OFF가 기본**(켜기 전엔 현재와 100% 동일).
  - 플래그 `feature_billing`(기본 false)·`billing_provider`(mock/toss/portone). `/config`에 billing 노출, 프런트 `FEATURES.billing`.
  - 모델 `Subscription` + 마이그레이션 `0015_subscription`(head). 서비스 `app/services/billing.py`(플랜 정의·provider 추상화·**mock**으로 키 없이 흐름 검증·toss/portone 스텁). `entitlement.is_premium`가 active 구독도 인정(플래그 ON 시).
  - API `/billing`(plans·me·checkout·confirm·cancel) — 전부 feature_billing ON일 때만, OFF면 404/enabled:false.
  - 리드 게이트(유료 가치): `/inquiries`가 **플래그 ON + 비프리미엄일 때만** 연락처 마스킹(`locked:true`, contact=null). OFF면 전체 노출(현재 동일). 대시보드에 🔒 표시 + "Pro 업그레이드"(mock 즉시 활성).
  - OFF 기본 불변식 확인: billing 404·plans disabled·마스킹 없음·업그레이드 버튼 숨김 → 현재와 동일.
  - 검증: 백엔드 compileall·py_compile PASS, 마이그레이션 head 단일(0015), 프런트 괄호 균형·verify_frontend PASS.
  - 문서: DATA(subscriptions)·README(모델)·ROADMAP·TESTING(L)·.env.example 갱신. (다음: 실 PG 키·웹훅 검증)
## v1.96 (2026-06-25)
- **문의/리드 기능(B2B 첫 매출 기반) — Phase 1**(모델·API·UI, 과금 게이트 OFF).
  - 모델 `Inquiry` + 마이그레이션 `0014_inquiry`(head). 소유자 비정규화(owner_account_id/owner_device_id)로 대시보드 조회 단순화.
  - API `/inquiries`: POST 생성(동의 필수·숨김/없는 매물 404), GET 목록(소유자만·연락처 포함), GET /summary(매물별 집계), POST /{id}/status(소유자만 new/read/contacted/closed). `account_from_auth` + device_id OR 매칭.
  - 프런트: 매물 상세에 `InquiryBox`("온라인 문의 남기기" → 이름·연락처·내용·동의 → 추적되는 리드 생성). 중개사 대시보드에 "받은 문의(리드)" 섹션·"받은 문의" Stat·매물별 문의 수·상태 버튼.
  - 개인정보: 연락처는 **소유자만 열람**·동의 필수·마케팅/제3자 제공 금지(9.A 준용). ⚠️ **개인정보처리방침에 '문의 연락처' 항목 추가 필요**(legal 검토·PRIVACY_VERSION·스토어 라벨) — 운영자/법무 후속.
  - 과금 게이트는 OFF(무료도 전체 열람). 다음 단계=결제(PG/구독) 연결 시 entitlement로 게이트.
  - 검증: 백엔드 compileall·py_compile PASS, 마이그레이션 head 단일, 프런트 괄호 균형·verify_frontend PASS.
  - 문서: DATA.md(inquiries)·README(모델)·ROADMAP·TESTING(K) 갱신.
## v1.95 (2026-06-25)
- **문서 전체 점검·정합화(코드 무변경)** — 핸드오버 문서를 현재 상태(v1.94)에 맞춤.
  - ROADMAP(SSOT): "출시 품질·수익화 토대(v1.65~v1.94)" 완료 섹션 추가(컷오버·PWA·접근성·페이지네이션·매물/중개사·출시도구). 수익화 스캐폴딩 상태 `[ ]`→`[x]`(OFF 기본), 프런트 빌드 항목 정본화 반영.
  - README: 프런트를 "Vite(main.jsx) 정본·app/web 동결·컷오버 구성 완료"로 수정(레거시 우선 서술 제거), 구조트리·컷오버 상태 갱신, TESTING.md·store/ 참조 추가.
  - CLAUDE.md: 검증 루틴을 frontend/src 정본 기준으로(app/web 편집 금지 명시), 프런트 서술 정합화, 중복 줄 정리.
  - QUICKSTART: Vite를 "UI 정본"으로 표기(레거시는 폴백·동결).
  - 점검 확인: 법적 문서 2벌(app/web·frontend/public) 동일 ✅, 문서 상호참조(.md/skills) 무결성 ✅.
## v1.94 (2026-06-25)
- **접근성 점검(대비·스크린리더 라벨) + 수정**.
  - 감사 결과: 색 대비(--ink/--muted/--teal/--up/--down)는 흰 배경·다크모드 모두 WCAG AA(약 5:1~14:1) 충족 → 색 변경 불필요. `lang="ko"`·`<img>` 없음(아이콘=인라인 SVG) 양호.
  - 아이콘 전용 닫기/지우기 버튼 6곳(× span): `aria-label`(닫기/검색어 지우기/사진 삭제) + `role/tabIndex/onKeyDown` 부여 — 스크린리더 명칭 + 키보드 조작 가능.
  - 폼 입력 라벨 연결: `LField`를 `<div>`→`<label>`로 변경해 모든 등록 폼 입력이 라벨과 프로그램적으로 연결(스크린리더가 "보증금(만원)" 등 읽음). 체크박스는 이미 label 래핑이라 양호.
  - 슬라이더(통근 시간/금리/기간)·숨김 파일 입력·댓글 수정 입력에 `aria-label` 추가. (aria-label 총 26)
  - 검증: 괄호 균형 · verify_frontend PASS. 잔여(경미): 장식용 › 셰브런(행 텍스트가 이름 제공)·매물 사진 배경이미지(인접 제목이 설명)는 후순위.
## v1.93 (2026-06-25)
- **PWA 앱 셸 캐싱 + 오프라인 셸 + 업데이트 배너**(의존성 없이 수제 SW).
  - sw.js 런타임 캐싱: navigate=네트워크 우선→캐시 셸(/)→offline.html, 정적 자산(/assets·/icons·manifest)=캐시 우선+백그라운드 갱신(SWR). **API 등은 미개입(항상 네트워크 — 시세 신선도·왜곡 방지)**. Vite 해시 자산이라 캐시 우선이 안전.
  - 버전드 캐시(`cj-shell-v2`), activate 시 구 캐시 정리. 푸시(push/notificationclick) 기능 보존.
  - 업데이트 배너: 새 SW 설치 감지 시 "새 버전이 준비됐어요 · 새로고침"(첫 설치 땐 미표시, `hadController` 가드). 운영 규칙=배포 시 sw.js VERSION 올리면 캐시 정리+배너 발화.
  - 문서: DEPLOY.md(PWA 전략·VERSION 규칙)·TESTING.md J 보강.
  - 검증: main.jsx 괄호 균형·verify_frontend PASS·sw.js node -c PASS. (런타임은 운영자 브라우저 확인 필요)
## v1.92 (2026-06-25)
- **접근성(키보드) 마무리** — 남아있던 인라인 클릭 행 전부 전환.
  - 검색 결과(지역·단지·매물), 검색홈·비교 단지 검색, 예산·통근 결과, 시세 단지목록·랭킹·거래·그룹토글, 청약 위젯 등 클릭 가능한 txrow/listrow 16곳에 `tabIndex/role="button"/onKeyDown=onEnter` 적용. 조건부(clickable) 행은 조건부로 부여.
  - 버튼과 핸들러가 겹치는 곳은 고유 앵커로 분리해 **이중 실행(키보드 중복 발동) 방지**. 네이티브 `<button>`에는 onKeyDown 미부여.
  - 결과: 키보드 미적용 클릭 행 0. (role/onKeyDown 다수)
  - 검증: 괄호 균형 · verify_frontend PASS.
## v1.91 (2026-06-25)
- **접근성 2차(키보드) + 빈 상태 CTA 확대**.
  - 키보드 네비게이션: 클릭 가능한 div를 키보드로 조작 가능하게(`tabIndex/role="button"/onKeyDown=onEnter`). 적용: 재사용 컴포넌트 ListingCard·PostCard·TourStop(→ 모든 매물/게시글/임장 단지), 홈 배너(거래 급상승·대장 아파트·최근 본 단지), 랭킹/최근 시트 행. (role 28·onKeyDown 18) Enter/Space로 열림 + v1.90 focus-visible로 포커스 표시.
  - 빈 상태 CTA 추가: 게시판 0건 → "+ 글쓰기"(비로그인 시 로그인 유도), 시세 검색 무결과(q) → "검색 지우기". (Empty action 2→5곳)
  - 검증: 괄호 균형 · verify_frontend PASS.
  - 남은 작업(정직): 검색결과·상세 등 흩어진 인라인 txrow/listrow 일부는 미전환 — 후속 마이크로 패스 대상.
## v1.90 (2026-06-25)
- **출시 품질 다듬기(접근성·빈상태·오프라인)**.
  - 접근성: 전역 `:focus-visible`(teal 2.5px 외곽선) 추가 — 키보드 포커스 가시성(WCAG 2.4.7). `prefers-reduced-motion` 시 애니메이션/트랜지션 최소화. (focus-visible 0→적용)
  - 빈 상태 CTA: 매물 목록이 0건일 때 "+ 매물 등록" 버튼을 빈 화면에 노출(`Empty` action 슬롯 활용, setMode in scope). ※ "표본 부족"류 빈 상태는 사용자 행동이 무의미해 제외.
  - PWA 오프라인 폴백: `frontend/public/offline.html`(정적 안내 페이지) + sw.js에 fetch 핸들러 추가. **navigate 요청만** 네트워크 우선·실패 시 오프라인 페이지 폴백. 자산·API는 가로채지 않아 스테일/업데이트 위험 없음. install 시 offline.html 1개만 캐시, activate 시 구 캐시 정리. (기존 push 기능 보존)
  - 검증: main.jsx 괄호 균형 · verify_frontend PASS · sw.js `node -c` PASS. TESTING.md J 섹션(브라우저/기기 확인법) 추가.
  - 적용 범위: frontend(dist) 기준. 레거시 app/web은 동결.
## v1.89 (2026-06-25)
- **UI 버그 5건 일괄 수정**(사용자 리포트).
  - ① 면적 단위(평/㎡) 연결: 단지상세 면적별 정보가 평으로 안 바뀌던 문제. 원인은 `unit==="pyeong"`(실제 값 `"py"`)라 조건이 항상 거짓. `areaTxt(a,unit)` 헬퍼 추가해 AreaSection 제목·전용 평형 텍스트·대출 면적 버튼·전세안전 기준 등 5곳을 `fmtArea(a.area,unit)` 기반으로 통일(평/㎡ 전환됨). ※ 소형/중형/대형 밴드 라벨(~60㎡)은 표준 범주라 유지. `res.affordability.label`은 면적 객체가 아니라 제외.
  - ② 단지상세 가로 스크롤 제거: 시트 콘텐츠 영역에 `overflowX:hidden`(SheetShell·Sheet 공통). 세로 스크롤·maxWidth 480 유지라 내용 손실 없음.
  - ③ 거래 급상승·대장 아파트 시트가 짧게 뜨던 것 수정: `Sheet`에 `fill`(height 93vh) 옵션 추가 → 통근(SheetShell)처럼 풀 높이로. RankSheet에 적용.
  - ④ 최근 본 단지를 거래 급상승처럼 표시: 기존 Collapsible 목록 → 배너+풀시트(RecentList 재작성).
  - ⑤ 거래 급상승·최근 본 단지 클릭 시 최대 10개: RankSheet·RecentList 모두 `slice(0,10)`.
  - 검증: 괄호 균형 · verify_frontend PASS. (프런트 변경은 npm run dev/build 후 반영)
## v1.88 (2026-06-25)
- **시세 단지 리스트 페이징 누락 수정**(v1.76에서 빠졌던 부분 — 사용자 지적).
  - 시세(PriceHub) **단지 목록(overview)** 이 전체 렌더되던 것을 `MoreList`(12개씩 더보기)로.
  - 같은 화면 **검색결과 단지 목록**도 `MoreList`(10개씩)로 일관 적용.
  - 이로써 긴 리스트 더보기 적용 누적: 매물(서버 페이지네이션)·청약·단지상세 최근거래·시세 거래그룹·시세 단지목록·시세 검색결과.
  - 검증: 괄호 균형 · verify_frontend PASS · MoreList 5곳.
## v1.87 (2026-06-25)
- **출시 준비(Phase 0) 코드 갭 보강**.
  - `scripts/preflight.py` 신설 — '인터넷 노출 안전성' 점검(JWT_SECRET 강도·ADMIN_TOKEN·CORS 와일드카드·DATABASE_URL·MOLIT 키·SPA 빌드·법적 페이지·아이콘 플레이스홀더). 앱 의존성 없이 동작(os.environ+.env+파일), FAIL 시 종료코드 1(파이프라인 게이트). doctor.py(데이터·시스템 헬스)와 역할 분리. 샌드박스 실행 검증(빈 설정→FAIL 1·WARN 7 정확 감지).
  - `store/` 스토어 메타데이터 템플릿 신설 — google-play.md·app-store.md(등록 문구·카테고리·키워드·Data safety/App Privacy 라벨 초안·심사 메모) + README(자산 체크리스트). 개인정보 라벨은 실제 동작 검증 필수임을 명시(특히 대출 9.A).
  - LAUNCH.md Phase 0에 preflight·store 사용 연결.
## v1.86 (2026-06-25)
- **출시→매출 단계 전략 문서(LAUNCH.md) 신설** — 코드 변경 없음.
  - Phase 0 출시준비(운영자 셋업·런타임 검증) → 1 웹/PWA 무료출시 → 2 스토어 앱 → 3 B2B 중개사 유료(첫 매출) → 4 소비자 프리미엄 → 5 제휴 → 6 광고.
  - 각 단계: 할 일·담당(운영자🧑‍💼/코드💻)·전환 KPI·비용. 가드레일(핵심 무료·값 불변·신뢰 우선·규제 자문)·정직한 한계 명시.
  - 핵심 순서: 무료로 신뢰·트래픽 먼저, 그 위에서 단계적 수익화. 첫 매출은 B2B 중개사가 가장 현실적.
  - README 포인터 추가.
## v1.85 (2026-06-25)
- **중개사 대시보드 v2-B: 매물 수정(PUT)**.
  - 백엔드: `PUT /listings/{id}`(owner-only). ListingIn 폼 항목만 갱신 → **status/views/is_sponsored/등록일/소유자는 보존**. `GET /{id}`은 숨김 매물도 **소유자면 조회 가능**(편집·복구용), 타인은 404.
  - 프런트: `ListingForm`에 `initial` 프롭(편집 초기화) + 저장 시 **PUT 분기**, 헤딩("매물 수정")·버튼("수정 저장") 라벨 대응. 대시보드 각 매물 "수정" 버튼 → 상세 GET으로 전체 필드 로드 후 폼 편집 → 저장 시 목록 자동 갱신.
  - 일반 등록 흐름(ListingsTab)은 그대로(initial 없으면 POST).
  - 검증: app+migrations 컴파일 OK · verify_frontend PASS · 괄호 균형.
- 정직한 한계: 문의/리드(고객 연락) 추적은 아직 없음 → v3 후보(문의 모델·연락 버튼·집계).
## v1.84 (2026-06-25)
- **중개사 대시보드 v2-A: 조회수 추적 + 상태관리**.
  - 백엔드: `Listing.views` 컬럼(마이그레이션 `0013_listing_views`). 상세 `GET /{id}`가 **외부 조회만 +1**(소유자 본인 조회는 제외 — 정직한 집계). `_row_full`에 `views` 노출.
  - 상태 변경 API `POST /listings/{id}/status`(owner-only, active/traded/hidden). 목록 API에 `manage=1`(소유자 관리목록=전체 상태) 추가 — **공개·일반 내매물 목록은 활성만 그대로 유지**.
  - 프런트 대시보드: **총 조회수·매물별 조회수** 표시, 상태관리 버튼(거래완료↔판매중, 숨김↔복구). 영구삭제 대신 **되돌릴 수 있는 상태 기반 관리**.
  - 검증: app+migrations 컴파일 OK · verify_frontend PASS · 괄호 균형.
## v1.83 (2026-06-25)
- **중개사 대시보드 v1(B2B 수익화 1순위 기능)** — 프런트 단독, 있는 데이터 기반(지표 미조작).
  - `AgentDashboard` 시트(SheetShell): 계정 메뉴에서 **role=agent에게만** "📊 중개사 대시보드" 진입.
  - 요약: 총 매물·활성 수·거래유형(매매/전세/월세) 분포·지역(구) 분포. `feature_ads` ON이면 "광고 노출" 수도 표시.
  - 내 매물 관리: `/listings?mine=1` 로 불러와 카드 목록(거래/가격/상태[거래완료·숨김]/광고 배지/등록일), **행 탭→매물 상세**(openListingId), **삭제**(전파 차단), **+ 매물 등록**(매물 탭 이동).
  - 접근성: 닫기 aria-label/키보드, 삭제 aria-label.
  - 검증: 괄호 균형 · verify_frontend PASS · 탭 키 listing 정합.
- 정직한 한계: **조회수·문의(리드) 추적은 백엔드에 없음** → v2로 분리(Listing.views 컬럼+상세 GET 증가+마이그레이션, 문의 모델 필요). 매물 수정(PUT) 미구현이라 관리에 삭제·재등록만.
## v1.82 (2026-06-25)
- **수익화 스캐폴딩(부록B) — 전부 피처 플래그 뒤, 기본 OFF=현재 동작 100% 동일(첫 출시 제외 가능)**. 구조/기능 테스트용.
  - 모델: `listings.is_sponsored`(bool·기본 false)·`priority`(int·0), `accounts.plan`(free|premium). 마이그레이션 `0012_monetization`(additive·멱등·server_default).
  - 매물 목록: 응답에 `is_sponsored`/`priority` 포함. 정렬은 **`feature_ads` ON일 때만** 후원·우선순위 우선(OFF면 최신순 그대로).
  - 권한: `app/services/entitlement.py`(`is_premium`/`require_premium`). `feature_monetization` OFF이면 항상 free. `/auth/me`(_acc)에 `plan`·`is_premium` 노출. **기존 기능은 아무것도 게이팅 안 함(구조만)**.
  - 프런트: `/config`의 `feature_flags`를 `FEATURES`로 읽어, ListingCard에 **"광고" 배지(amber)** = `FEATURES.ads && x.is_sponsored`일 때만.
  - 테스트용 admin: `POST /admin/test/sponsor`(매물 광고 토글)·`POST /admin/test/plan`(계정 plan) — admin_token 보호.
  - 객관성 가드레일: sponsored는 **표시 순서·배지만**, 시세/추천 값은 불변.
  - 문서: MONETIZATION.md 부록 반영, TESTING.md §H(테스트 절차), CLAUDE.md 상태.
  - 검증: app+migrations 컴파일 OK · verify_frontend PASS · 플래그 기본 OFF 확인.
## v1.81 (2026-06-25)
- **수익화 전략 문서(MONETIZATION.md) 신설** — 코드 변경 없음(전략 정리).
  - 기능 중심 전략: 핵심 데이터는 무료 유지, A)중개사 B2B(최우선·신뢰위험 낮음) → B)소비자 프리미엄 구독 → C)제휴(대출/이사, 고규제) → D)익명 집계 데이터 → E)광고(최후).
  - 현재 구조 근거 명시: `/config` 피처플래그(ads·monetization, 기본 OFF)·agent role은 있음 / sponsored·entitlement·결제는 없음.
  - 객관성 가드레일: sponsored는 표시 순서·배지만, 시세/추천 값 불변. 제휴·광고 명확 표기. 금융 제휴 법무 검토.
  - 단계 로드맵(Phase 0 무료 출시 → 1 B2B → 2 프리미엄 → 3 제휴 → 4 광고), 부록 B 정합 스캐폴딩 후보 정리.
  - README에 포인터 추가.
## v1.80 (2026-06-25)
- **접근성 1차(②-3)** — 큰 단일 파일 전면 개편 대신 안전·고효과 항목 중심.
  - Icon 컴포넌트 전역에 `aria-hidden=true`·`focusable=false` → 모든 장식 아이콘을 스크린리더가 건너뜀(SR 경험 개선).
  - 닫기(×) 버튼 3곳 + 홈 진입 카드 3개(통근·예산·대출)에 `aria-label`·`role="button"`·`tabIndex={0}` + **Enter/Space 키보드 활성화**(`onEnter` 헬퍼). 마우스 없이 조작 가능.
  - 하단 네비에 `role="navigation"` `aria-label`.
  - 온보딩 환영 카드 닫기에도 aria-label(이미 적용).
  - 검증: 괄호 균형 · verify_frontend PASS · aria-label 4→12 · onKeyDown 6.
  - ⚠️ 정직한 범위: 전면 WCAG 감사(모든 클릭 div 키보드화·색 대비·focus-visible·실제 스크린리더 테스트)는 더 큰 후속 작업으로 남김.
## v1.79 (2026-06-25)
- **온보딩(②-2, 첫 방문 안내)**. 통근·예산·대출 같은 숨은 강력기능의 발견성 개선.
  - 홈 최상단에 **첫 방문 시에만** 뜨는 dismissible 환영 카드. "통근시간으로/예산으로/대출 한도" 칩을 눌러 해당 시트로 바로 진입.
  - × 로 닫으면 `safeStore`(`cj_onboard_v1`)에 기록해 다시 표시 안 함. 모달이 아니라 카드라 흐름을 막지 않음.
  - 검증: 괄호 균형 · verify_frontend PASS.
## v1.78 (2026-06-25)
- **대출 진입 노출(②-1, 발견성 개선)**. 핵심 차별화인 대출 계산이 단지상세에만 묻혀 있던 문제 해결.
  - 홈에 "내 대출 한도 계산" 진입 카드 추가(통근·예산 카드와 동일 패턴/스타일).
  - `LoanSheet` 오버레이 신설(BudgetSheet 미러링, SheetShell) → 카드 탭 시 전체 시트로 대출 계산기 표시. `Loan`은 단독 모드(직접 매매가 입력) 동작.
  - App 배선: `loanOpen` 상태, Board에 `onLoan` 전달, 네비 숨김 조건에 추가, 단지 추천 시 `openComplex` 연결.
  - 뉴스·정책: 이미 홈 '오늘의 정보'(defaultOpen)에 노출되어 별도 작업 없음.
  - 검증: 괄호 균형 · verify_frontend PASS · LoanSheet 정의1/사용1.
## v1.77 (2026-06-25)
- **매물 리스트 서버 페이지네이션 실연결**(v1.76의 백엔드 offset 소비).
  - ListingsTab: 페이지 크기 20. 필터 변경 시 `offset=0` 리셋 후 로드, "더보기"는 `offset=현재개수`로 다음 페이지를 받아 **append**(누적). 응답 `has_more`로 더보기 노출 제어, 로딩 중 "불러오는 중…" 표시. 데모 폴백 시 더보기 비노출.
  - 매물은 클라이언트 더보기(MoreList) 대신 **서버 더보기**로 전환(50 캡 너머 수신). 한정 데이터인 청약·단지상세 최근거래·시세 거래그룹은 MoreList(클라이언트 더보기) 유지.
  - 필터 파라미터를 `filterParams()`로 분리해 load/loadMore가 공유(중복 제거).
  - 검증: 괄호 균형 · verify_frontend PASS · MoreList 사용 3 · has_more 소비 3.
## v1.76 (2026-06-25)
- **긴 리스트 페이징(UI 보강) + 백엔드 페이징 준비**.
  - 프런트(단일 소스 `frontend/src/main.jsx`): 재사용 `MoreList`(더보기·증분 로드) 추가 → **매물·청약·단지상세 평형별 최근거래·시세 거래그룹**에 적용. 처음 4~6개만 렌더하고 "더보기 (남은 N개)"로 step씩 추가 → 모바일 길이·렌더 DOM 부담 동시 개선. 리스트 변경 시 자동 초기화.
  - 기존에 이미 페이징되던 것(랭킹 RankSheet·시세 BandList 그룹 8/페이지)은 유지. 중복 페이저 없이 보완.
  - 백엔드(레거시·dist 공통): `/transactions`·`/listings`에 **`offset` 파라미터 추가(기본 0 = 동작 불변)** + 응답에 `offset`·`has_more` → 50개 캡 너머도 "다음 페이지"로 분할 수신 가능(사용자 요청한 "백엔드에서 나눠 보내기" 준비). 응답은 기존 `{items,count}`에 필드만 추가(하위호환).
  - 합리적 설계: 프런트 더보기가 렌더 부담을 먼저 해소(≤50 캡 내), 데이터가 50을 상시 초과할 때 프런트가 `offset`로 다음 페이지를 이어받는 2단 구조.
  - 검증: app 컴파일 OK · verify_frontend PASS · 괄호 균형 · MoreList 정의1/사용4.
## v1.75 (2026-06-25)
- **컷오버 확정 — 프로덕션이 Vite dist를 서빙, 소스 단일화**.
  - **Dockerfile 멀티스테이지화**: ① node로 `frontend` 빌드 → ② 백엔드 런타임에 `dist` 포함 + `ENV WEB_DIR=/app/frontend/dist`. 즉 배포 이미지가 레거시가 아닌 **빌드된 dist를 서빙**(컨테이너가 컷오버를 보장). 빌드 머신엔 Docker만 있으면 됨(npm 단계 내장).
  - **단일 소스 전환**: 웹 UI 권위 소스 = `frontend/src/`. 레거시 `app/web/index.html`은 **동결(편집 금지)**, bare 로컬 폴백으로만 잔존(한 사이클 후 제거 예정).
  - `scripts/verify_frontend.py`: 레거시 대조를 **동결 참조(정보용)**로 완화(향후 단일소스 편집으로 차이 증가 정상), main.jsx 구조 검증(괄호·import·index.html)은 하드 유지. 레거시 없어도 동작.
  - 문서: `CUTOVER.md`(확정 상태·단일소스·컨테이너 검증), `CLAUDE.md`(단일소스 관례), `DEPLOY.md`(멀티스테이지·/assets), `ROADMAP.md`(항목3 [x]).
  - 검증: app 컴파일 OK · verify_frontend PASS(단일소스 모드) · Dockerfile 스테이지/dist/WEB_DIR 확인.
  - ⚠️ 남은 1개 미검증: 샌드박스 도커 빌드·기동 불가 → **운영 머신에서 컨테이너 띄워** 라우트·/assets·/health 1회 확인(CUTOVER.md 체크리스트). 통과 시 컷오버 完了.
## v1.74 (2026-06-25)
- **배포·운영 필수 구성**(기본 동작 불변, 추가/문서 위주).
  - **Dockerfile** 신설(python:3.12-slim, 비루트 appuser, `uvicorn --workers ${WEB_CONCURRENCY:-2}`) + **.dockerignore**(.env·산출물 제외). compose가 참조하던 누락 이미지 해소.
  - **docker-compose.prod.yml** 신설: web(다중 워커)+scheduler(단일, 중복수집 방지)+Postgres. 기존 dev compose는 그대로.
  - **CORS 환경변수화**(`app/main.py`): `CORS_ORIGINS` 콤마구분, 미설정 시 `*`(개발 불변). 운영은 도메인+앱 origin으로 좁힘.
  - **DEPLOY.md** 신설: 아키텍처·필수 환경변수 표·빌드/실행(compose, alembic upgrade)·Nginx HTTPS·배포 전 점검 체크리스트·운영(스케줄러 단일·백업·모니터링·롤백)·보안 체크.
  - `.env.example`에 `CORS_ORIGINS`·`WEB_DIR`·`WEB_CONCURRENCY` 추가. README·ROADMAP·CLAUDE 동기화.
  - 검증: app 컴파일 OK · CORS 로직(기본 `*`/운영 좁힘) · compose YAML 유효(db/web/scheduler) · Dockerfile 비루트 · verify_frontend PASS(프런트 무영향).
  - ⚠️ 정직한 한계: 샌드박스(네트워크 X)에서 **이미지 빌드·기동은 미검증** → 운영 머신에서 `DEPLOY.md` 절차로 확인.
## v1.73 (2026-06-25)
- **에러바운더리 추가**(첫 기능 보강 — 안정성). 컴포넌트 렌더 오류 시 **전체 백스크린 대신 "일시적인 오류" 카드 + 새로고침**. 정상 동작 시 UI 변화 없음(순수 추가).
  - 첫 클래스 컴포넌트(`ErrorBoundary extends React.Component`, getDerivedStateFromError/componentDidCatch) — 레거시(Babel)·main.jsx(실 React) 양쪽 동작. 참조 색상은 모듈 상수(INK/MUTED/TEAL, var(--*)).
  - 루트 렌더를 `<ErrorBoundary><App/></ErrorBoundary>`로 래핑.
  - **컷오버 전이라 레거시·main.jsx 양쪽에 동일 반영** → 둘의 1줄 차(API) 불변 유지(verify_frontend PASS, 본문 3706=3706). 괄호 균형·상수 정의 확인.
  - 참고: 이번이 첫 의도적 기능 변경 → 레거시 `app/web/index.html`은 더 이상 v1.65 원본(/tmp/orig)과 동일하지 않음. 이후 무결성 기준은 verify_frontend(main.jsx↔현 레거시 1줄 차).
  - TESTING.md D에 에러바운더리 확인 항목 추가.
## v1.72 (2026-06-25)
- **컷오버 준비 — 레거시 HTML → Vite dist 서빙 전환 토대**(기본 동작 100% 불변).
  - `app/main.py`: `WEB_DIR` 환경변수화(기본=`app/web` 그대로). `WEB_DIR=frontend/dist`(assets/ 보유)일 때만 `SPA_MODE` → SPA 정적 마운트(`/assets`·manifest·icons). env 지정해도 assets 없으면 비활성(안전장치). 명시 라우트·API 라우터가 우선 매칭되어 가려지지 않게 마운트는 파일 끝에 추가.
  - `CUTOVER.md` 신설: 전환 절차(build → `WEB_DIR=...dist` → 재시작) · 런타임 검증 체크리스트 · **즉시 롤백(`unset WEB_DIR`, 코드 변경 0)** · 컷오버 후 소스 일원화(`frontend/src/` 단일) · 모듈 분리 가이드.
  - 문서 동기화: `CLAUDE.md`(WEB_DIR·CUTOVER 포인터), `TESTING.md`(E-2 컷오버 검증 절), `ROADMAP.md`(항목3 컷오버 준비 완료).
  - 검증: app/ 컴파일 OK · WEB_DIR/SPA_MODE 로직(기본 비활성·dist 활성·assets없음 비활성) 확인 · 레거시 index.html 원본 동일 · verify_frontend PASS.
  - ⚠️ 정직한 한계: 샌드박스에 fastapi 미설치 → **런타임 서빙 동작은 개발 머신에서** `CUTOVER.md` 절차로 확인 필요(여기선 문법·전환 로직만).
## v1.71 (2026-06-24)
- **테스트 방법 기록 + 실행 가능한 검증 도구**(앱 동작 변경 없음 — 테스트 툴/문서만).
  - `TESTING.md` 신설: 전 레이어 테스트 방법 단일 기록 — 어디서 무엇을 도는지(샌드박스/PC/실기기/Mac), A 백엔드·실데이터(doctor·verify_region_codes·run_collect·/health·/status/data), B 회귀(pytest·compileall·CI), C 오프라인 무결성(verify_frontend·레거시 괄호스캔), D 프런트 빌드(npm + UI 체크리스트), E PWA(DevTools Application·설치), F Capacitor/Android(CAPACITOR.md 연계), G Phase D 예정, 릴리스 전 체크리스트.
  - `scripts/verify_frontend.py` 신설: `python -m scripts.verify_frontend` — main.jsx 본문이 레거시와 **API 1줄만 다름** + 괄호 균형 + React/ReactDOM import 커버 + index.html(CDN 제거·module·root·manifest·SW) 자동 확인. 실행 PASS 확인됨.
  - `CLAUDE.md` §6에 verify_frontend·TESTING.md 포인터 추가.
  - 비파괴: 레거시 `app/web/index.html` 원본 동일, `frontend/src/main.jsx` 본문 1줄차(불변) 재확인.
## v1.70 (2026-06-24)
- **모바일 앱 Phase C — Capacitor 셸 스캐폴딩**(설정·런북만. 네이티브 `android/` 생성·빌드는 개발 머신에서).
  - `frontend/capacitor.config.json`(webDir=dist·appId placeholder·SplashScreen), package.json에 `cap:sync/android/ios` 스크립트.
  - `frontend/.env.production.example`(네이티브 빌드용 `VITE_API_BASE` 절대 URL — 같은 출처가 아니므로 필수), `.gitignore`에 `.env.production`·`/android`·`/ios`.
  - `frontend/CAPACITOR.md` 런북: 선행조건(A/B 빌드 성공)·설치(최신)·appId 확정·`cap add android`·네이티브 빌드(API base)·sync/open·**노치 세이프에어리어 CSS(런북에만, 미적용)**·CORS·아이콘/스플래시·다음(D iOS/푸시·E 심사·F OTA).
  - 비파괴: 레거시·백엔드·`main.jsx` 본문·`frontend/index.html` 무변경(세이프에어리어는 자동 적용 안 하고 런북에 명시 → 기기 검증 후 적용).
  - ⚠️ 이 환경에선 `npx cap add android`·Gradle 빌드 불가(Android SDK·네트워크 필요) → 실제 네이티브 빌드는 개발 머신. Capacitor는 A/B 빌드 검증 후 진행.
## v1.69 (2026-06-24)
- **문서 동기화(드리프트 제거)** — 코드 변경 없음, 기존 서술 보존 + 구조·상태만 정확 반영.
  - `README.md`: 기술스택 표에 `frontend/` Vite 빌드 추가, 프로젝트 구조 트리에 `frontend/` 추가, 구조점검 표 ①(프런트 빌드) 상태를 Phase A·B 완료로 갱신 + `MOBILE_APP_STRATEGY.md` 안내.
  - `QUICKSTART.md`: **폐기된 Expo(`cheongju-mobile`) 안내 교체** → 새 프런트(Vite) 실행·빌드 섹션 + 네이티브(Capacitor) 안내.
  - `ROADMAP.md`: 프런트 빌드(프로덕션준비 3·6대구조 ①) 상태 갱신, M5 앱 항목을 "RN 폐기→Capacitor 확정, Phase A·B 완료, C~F 남음"으로 정정.
  - `CLAUDE.md`: 스택에 frontend 빌드(마이그레이션 중) **인수인계 규칙**(레거시가 권위·컷오버 전 수정 위치·비파괴 원칙) 추가, 레포 트리에 `frontend/`, 현재상태에 Phase A·B 완료 + Capacitor 확정 반영.
  - 검증: 레거시 `app/web/index.html` 원본과 동일, `frontend/src/main.jsx` 본문 1줄차(불변) 재확인.
## v1.68 (2026-06-24)
- **모바일 앱 Phase B — 설치형 PWA**(비파괴: `frontend/`에만 추가, 레거시·백엔드·`main.jsx` 본문 무변경).
  - `frontend/public/manifest.webmanifest` 추가(name·short_name·start_url·display=standalone·theme_color #0F766E·background #fff·아이콘 3종 any/maskable).
  - 아이콘 생성: `icon-192/512`, `icon-maskable-512`(안전영역 패딩), `apple-touch-icon-180`(브랜드 틸 + 상승추이 마크). ⚠️ 기능용 기본 아이콘 — 스토어 제출 전 디자인 교체 권장.
  - `frontend/index.html` head에 manifest·theme-color·apple-touch-icon·apple PWA 메타·favicon 추가, body에 **로드 시 서비스워커 등록 스크립트**(설치형 요건; 기존 푸시 코드의 register와 멱등). main.jsx는 손대지 않음.
  - 서비스워커(`sw.js`)는 푸시 전용 그대로 유지(설치 가능성엔 매니페스트+아이콘+등록 SW로 충분). 오프라인 캐싱은 후행 선택.
  - 검증(오프라인): manifest JSON 유효·필수필드·maskable 포함, 아이콘 4종 생성·크기 확인, index.html 삽입 확인, main.jsx 본문 1줄차(불변), 레거시 동일.
  - ⚠️ 실제 설치 가능 여부(Android 크롬 "홈 화면에 추가" 독립실행, iOS 사파리 설치)는 **HTTPS 환경 + 실제 빌드**에서 확인 필요. 네트워크 차단으로 여기선 빌드 미실행.
## v1.67 (2026-06-24)
- **모바일 앱 Phase A — Vite 빌드 토대(`frontend/`) 추가**(비파괴: 기존 `app/web/index.html`·백엔드 무변경).
  - 목적: 브라우저 런타임 Babel + CDN 의존 제거 → `npm run build`로 `dist/` 산출(스토어/Capacitor의 공통 선행조건).
  - `frontend/src/main.jsx` = 기존 인라인 스크립트 **본문 무변경**(원본 대비 diff 결과 **딱 1줄**만 차이: `const API="";` → `import.meta.env.VITE_API_BASE` 폴백 `""`). 상단에 `import React`/`createRoot`(react-dom/client)/`createPortal`(react-dom) 추가.
  - `frontend/index.html` = React/ReactDOM/Babel CDN 제거 + module 스크립트. Pretendard는 Phase B에서 번들(현재 CDN 유지).
  - `package.json`(react 18.2.0·vite 5·@vitejs/plugin-react 4) / `vite.config.js` / `.env.development`(dev API base) / `README.md`(빌드·검증·컷오버 가이드).
  - 검증(오프라인 가능 범위): 본문 무변경 diff, 괄호 균형, React/ReactDOM 사용처가 import로 전부 커버됨(특히 `createPortal` 누락 버그를 사전 발견·수정), 외부 빌드 의존 없음(네이버 지도는 런타임 주입, 카카오는 OAuth 설정값).
  - ⚠️ 네트워크 차단 환경이라 `npm install`/`npm run build`는 **미실행** → 개발 머신에서 README 체크리스트로 최종 확인 필요. 검증 후 컷오버(레거시 index.html 제거).
## v1.66 (2026-06-24)
- **버그픽스(치명) — 홈 대시보드 데드락 제거**: `stats.trending_complexes`('거래 급상승')에 `@stat_cached()` 데코레이터가 **두 번** 적용돼 있던 문제를 한 줄 제거로 수정.
  - 원인: stat_cached 캐시 키는 `fn.__qualname__` 기준이라 두 겹이 **같은 키**를 공유. 캐시 미스 시 바깥 wrapper가 그 키의 **비재진입 락**을 잡은 채 loader로 안쪽 wrapper를 호출 → 안쪽이 같은 락을 재획득하려다 **데드락**. 영향: `GET /dashboard/board`(앱 첫 화면)가 데이터 버전마다 첫 요청에서 정지.
  - 회귀 방지: `tests/test_stats_decorator.py`(app 전체 '연속 동일 데코레이터' 0건 구조검사 + trending_complexes 데드락 워치독).
  - 이 버전은 원본 v1.65에 위 버그픽스만 적용한 것입니다. (검토 과정에서 시험했던 전월세 전환율 관련 추가분은 전부 제거하고 원래 홈 화면 기능·UI를 그대로 복원했습니다.)
## v1.65 (2026-06-22)
- **공유·SEO 진입 페이지(사용자 획득) — SPA 영향 없음**: 백엔드가 서버 렌더 진입 페이지를 추가 제공.
  - `GET /r/{lawd_cd}`(지역 시세 요약)·`/c/{lawd_cd}/{name}`(단지 시세) — `<title>`·description·**Open Graph/Twitter 메타**(카카오톡·검색 미리보기) + 핵심 시세(중앙값·전세가율·거래수) + 주요 단지 링크 + '앱에서 보기' CTA. 데이터 없으면 '수집 중' 안전 표기, 모든 동적 문자열 html.escape(인젝션 방지).
  - `GET /sitemap.xml`(지역+주요 단지 최대 30/구)·`/robots.txt` — 검색엔진 색인.
  - stats.price_overview·complex_detail 재사용. 절대 URL은 PUBLIC_BASE_URL(없으면 요청 호스트 추론). SPA(/) 및 기존 API 불변.
  - 효과: ① 구글 색인(검색 유입) ② 카톡 공유 리치 미리보기 ③ 재작성 없이 발견·공유 통로 확보. 테스트 tests/test_landing.py. .env.example·skills·ROADMAP 동기화.
## v1.64 (2026-06-22)
- **데이터 파이프라인 견고화(실데이터 launch 대비) — 기존 동작 영향 없음**: 정규화 필드 미매핑을 '조용히'가 아니라 '시끄럽고 자가진단되게'.
  - `molit/normalize.py`에 선택적 `NormalizationReport` 추가. `normalize_row(..., report=r)`로 넘길 때만 핵심 필드 미매핑(deal_amount/contract_date/exclusive_area/complex_name) 집계 + 원본 키 샘플 보존. **report 미전달 시 반환·로직 완전 동일**(기존 호출부 무영향). 유형별 오탐 방지(전월세·단독다가구 제외).
  - `collect_live` 가 수집 중 report 누적 → 반환 `mapping`·last_collect.mapping_misses·미매핑 시 단일 WARNING. JobRun.stats(/admin/runs)에서 확인.
  - `scripts/doctor.py`: 실데이터 표본을 정규화해 '정규화 필드 매핑' 항목으로 즉시 진단(미매핑 ❌ + FIELD_CANDIDATES 보강 안내). 실데이터 1순위 리스크(필드 불일치로 데이터가 조용히 비는 것)를 배포 시 바로 포착.
  - 테스트 tests/test_normalize_report.py(5종, 순수·오프라인 통과). skills/data-and-sources.md 문서화.
## v1.63 (2026-06-22)
- **문서 현행화(코드↔문서 동기화)**: 최근 ~20개 버전(시세 서버집계·생활권·바텀시트 통일·청약상세·푸시·모니터링·백업·임장·doctor)이 빠져 있던 내부 지침을 코드 현실에 맞춰 갱신. 코드 변경 없음.
  - skills/deploy-and-db.md: 마이그레이션 이력(0001~0011), 웹푸시·모니터링·백업·doctor 실제 패턴 추가.
  - skills/aggregations.md: price_overview(시세 서버집계)·생활권 점수(living) 규칙 추가.
  - skills/frontend.md: SheetShell 바텀시트/스와이프 통일·시세 드릴다운·상세 위젯·임장·푸시토글·데모폴백 보강.
  - skills/README.md: 레포 지도 현행화 + 원칙 7 '문서 동기화(필수)' 추가.
  - CLAUDE.md: §5 모델(PushSubscription·JobRun·Commute*)·§8 진행상태·§9 skills 색인(deploy/frontend/testing) 보강.
  - ROADMAP.md: 완료 항목 체크 + 'v1.50~v1.62 완료 로그' 추가(진행 SSOT 정합).
## v1.62 (2026-06-21)
- **배포 자가진단(scripts/doctor.py)**: 운영 PC에서 전체 스택을 한 번에 점검 — 설정·DB 연결·핵심 테이블(마이그레이션)·지역코드 실조회(MOLIT 1회)·데이터 신선도/건수·연동 키(카카오/지도/푸시/Sentry/경보)·백업 준비(pg_dump·쓰기권한)·관리자 토큰. 각 항목 ✅/⚠️/❌, ❌ 있으면 종료코드 1. 그동안 샌드박스에서 검증 불가했던 푸시·모니터링·백업·수집을 실서버에서 한 명령으로 확인. `--skip-live`로 외부호출 생략. monitoring.system_status·MolitClient·CHEONGJU_DISTRICTS 재사용. OPERATIONS.md 최상단에 사용 안내.
## v1.61 (2026-06-21)
- **임장 도우미(차별화)**: 관심 단지를 한 번에 둘러보는 '임장 코스 + 체크리스트'. 홈 '관심 단지'에 🧭 진입 버튼 → 바텀시트(TourSheet)에서 단지를 순번 코스로 나열, 단지별 임장 체크리스트(채광·소음·누수·주차·관리상태·동선 등 9항목)와 메모를 제공. 체크/메모는 기기에 저장(safeStore, 서버 전송 없음)되어 현장에서 그대로 확인 가능. 단지 탭 시 상세로 이동. 분석→실제 방문 전환(우리 약점)을 메우는 기능.
## v1.60 (2026-06-21)
- **백업 상태를 모니터링에 통합**: 백업/복구는 이미 구현돼 있음(scripts/backup.py·restore.py, 스케줄러 자동 백업 `SCHEDULER_RUN_BACKUP`, pg_dump/sqlite 분기, 보존정책, /admin/runs?name=backup). 이번엔 `system_status`가 **최근 백업 실패를 경고로 표시**하고 `ok` 판정에 반영하도록 보강 → `/admin/monitor`에서 수집뿐 아니라 백업 건강도까지 한눈에 확인.
- 정리: config의 백업 키 중복 정의 제거(backup_dir/backup_keep/scheduler_run_backup 단일화).
## v1.59 (2026-06-21)
- **관측성(모니터링) 설계·구현 — 무인 운영 대비**:
  - **실행 이력**: JobRun 모델 + 마이그레이션(0011_jobrun). 수집/지오코딩 등 배치의 성공·실패·소요·통계·오류를 기록.
  - **monitoring 서비스**: `record_job`(배치 감싸 기록+실패 시 경보), `alert`(ERROR 로그 + 웹훅 Slack/Discord), `system_status`(DB·데이터 신선도·최근 실행·카운트·연동여부·경고 통합), `recent_runs`.
  - **스케줄러 연결**: 수집·지오코딩을 record_job으로 감싸 자동 기록·경보(지오코딩 키 없음은 skip 처리).
  - **관리자 API/UI**: `GET /admin/monitor`(통합 상태), `GET /admin/runs`(실행 이력) — ADMIN_TOKEN 보호. /admin/ui에 '시스템 상태·실행 이력' 버튼 추가.
  - **에러 모니터링**: SENTRY_DSN 설정 시 Sentry 초기화(미설정·미설치 시 무동작). requirements에 sentry-sdk.
  - config: sentry_dsn·alert_webhook_url·data_stale_days. .env.example·OPERATIONS.md 문서화. 테스트 tests/test_monitoring.py.
  - 키 게이팅: 모든 경보/모니터링은 키 없어도 앱 정상 동작(로그만). 개인정보·키 값 미노출.
## v1.58 (2026-06-21)
- **웹푸시(푸시 알림) 구현 — 재방문 핵심**: 관심 단지 신고가·새 실거래를 휴대폰/브라우저 푸시로 발송(표준 웹푸시/VAPID, 유료 서비스 불필요).
  - 백엔드: PushSubscription 모델 + 마이그레이션(0010_push), services/push.py(pywebpush 지연 import·키 게이팅·만료 자동정리), API `/push/vapid|subscribe|unsubscribe|test`, notify_transactions에 발송 연결(알림 생성 시 해당 계정 구독으로 푸시; 실패해도 수집·알림 불영향). config VAPID 키 + push_enabled. scripts/gen_vapid.py 키 생성기. requirements에 pywebpush.
  - 프런트: 서비스워커(/sw.js, push·notificationclick), 구독/해지 헬퍼, 알림함 상단 '푸시 알림 켜기' 토글. 권한 요청·구독 저장·해지 일괄 처리.
  - 안전장치: VAPID 키 없으면 푸시만 비활성(앱·다른 기능 정상). HTTPS 필요. iOS는 홈 화면 추가(PWA) 후 동작. 테스트 tests/test_push.py(no-op 경로). 운영 절차는 OPERATIONS.md 참고.
## v1.57 (2026-06-21)
- **검색 → 하단 시트 통일**: 통합 검색을 전체화면 오버레이에서 공용 바텀시트(SheetShell)로 변경. 검색 입력창은 시트 헤더(핸들 아래 고정), 결과/검색홈은 본문 스크롤. 아래로 스와이프·배경 탭·취소로 닫힘 → 앱 전체 오버레이가 한 패턴으로 통일.
## v1.56 (2026-06-21)
- **청약 상세 추가(마감 포함 열람)**: 청약/분양 카드를 탭하면 상세 시트(SubDetail/SubSheet)가 열림 — 지역·청약기간·총공급·분양가·경쟁률·최저가점, 주택형별(세대·분양가·경쟁률·최저/평균가점), 청약홈 바로가기, 출처 고지. **마감된 공고도 결과·기록 참고용으로 열람 가능**(상단에 마감 안내). 카드에 › 표시 + 탭 가능.
- **상세 화면 뒤로가기 버튼 제거**: 시트로 전환된 상세(단지·매물·게시판)에서 상단 '뒤로(‹)' 버튼 삭제 — 시트는 핸들·아래로 스와이프·배경 탭으로 닫음(중복 제거). 전체화면 폼(매물 등록)·작성자 보기의 뒤로 버튼은 유지.
## v1.55 (2026-06-21)
- **게시판 상세 → 바텀시트 통일**: 커뮤니티(게시판) 글 상세도 전체화면 전환에서 바텀시트(PostSheet)로 변경. 리스트 유지·맥락 보존. 글 편집/작성자 보기는 기존 전체화면 흐름 유지.
- **시트 공용화(SheetShell) + 아래로 스와이프 닫기**: 단지·매물·게시판·통근·예산 5개 시트의 중복 마크업을 공용 `SheetShell`로 통합(유지보수·일관성). 스크롤이 맨 위일 때 **아래로 끌어내리면(터치 스와이프) 시트가 닫힘**(110px 이상 시 닫기, 미만이면 스르륵 복귀). 내부 스크롤·버튼과 충돌하지 않도록 '맨 위에서 아래로'일 때만 드래그 인식. 기존 배경 탭·핸들·× 닫기 그대로.
## v1.54 (2026-06-21)
- **매물 상세 → 바텀시트 통일**: 매물 게시판의 상세화면을 전체화면 전환에서 단지·통근·예산과 동일한 **바텀시트(ListingSheet, 93vh·드래그핸들·dim 배경)**로 변경. 리스트가 유지된 채 위로 시트가 떠 맥락 유지·뒤로가기 일관성 확보. 상단 BackBtn·핸들·배경 탭으로 닫힘. 외부 딥링크(openId)·카드 탭 모두 시트로 표시.
## v1.53 (2026-06-21)
- **시세 조건 변경 반응속도 개선**: 백엔드 미연결(demo) 상태에선 /price/overview 요청을 건너뛰고 즉시 demoOverview를 사용 → 구·유형·평형을 바꿀 때마다 요청 실패를 기다리던 지연 제거(미리보기 체감 개선). 실서버(live)에선 정상 요청하되 4초 안전 타임아웃(AbortController)으로 행 걸림 방지 후 폴백. 로딩 중에는 직전 결과를 유지하고 '불러오는 중…' 표시(빈 화면 깜빡임 없음).
## v1.52 (2026-06-21)
- **버그픽스(시세 탭 빈 화면)**: 시세 탭의 /price/overview 폴백에서 catch 가드가 `if(on)return`으로 뒤집혀 있어, 백엔드 미연결(미리보기/네트워크 실패) 시 demoOverview 폴백이 깔리지 않고 데이터가 비어 보이던 문제 수정(`if(!on)return`). 실서버 정상 응답 시 빈 결과는 그대로 '거래 0건' 안내로 노출(왜곡 없음).
## v1.51 (2026-06-21)
- **생활권 점수(차별화)**: 단지 상세에 반경 1.5km 내 인프라 접근성을 투명하게 점수화한 '생활권 점수' 추가. 교통(지하철)·편의(마트)·학교·의료(병원) 4개 카테고리의 **최단 거리 기반**(300m 이내 100점, 1.5km 40점 선형, 반경 내 없으면 0점) 가중 평균(0~100)+등급(최상/좋음/보통/아쉬움). 카테고리별 점수·최단거리·개수를 함께 표시해 '왜 이 점수인지' 공개(블랙박스 아님). 실거주 만족도와 다를 수 있는 거리 기준 참고치임을 고지(출처: 카카오 장소).
  - 백엔드: services/living.py(`living_score(poi)`), /complex/detail 응답에 living_score 포함(좌표+카카오 키 있을 때, 없으면 None). 프런트: LivingScore 카드(인근 인프라 위). 데모는 표본 배지.
  - 테스트 tests/test_living.py(순수 로직 3종). 실서버에선 카카오 키+지오코딩 좌표가 있어야 실제 점수가 계산됨.
## v1.50 (2026-06-21)
- **시세 집계 서버 이전(확장성)**: 시세 탭이 거래 500건을 클라이언트로 받아 집계하던 구조를 **서버 집계 API `GET /price/overview`**(stats.price_overview, 캐시 적용)로 대체. 구/유형/평형대를 넘기면 윈도우(최근 N개월) 전체 실거래로 구 요약(중앙 매매·전세가율·거래량·전월 등락)과 단지 리스트를 집계해 반환 → 데이터·지역 확장 시에도 표본 왜곡·페이로드 폭증 없음. 프런트는 이 API 사용(검색·정렬은 구 단위 소목록에서 클라이언트 처리), 무네트워크 시 demoOverview 폴백.
  - 검증은 실서버에서 `GET /price/overview?lawd_cd=43113&property_type=apartment` 및 pytest 권장(샌드박스는 DB 불가). demoOverview는 node로 동등성 확인.
## v1.49 (2026-06-21)
- **시세 탭 전면 개편 — ‘지역 → 단지’ 드릴다운**(군더더기 제거). 기존 3서브탭(리스트·지도·랭킹)+필터 6종 → 핵심 흐름으로 정리:
  - 상단 **구 칩**(전체·상당·서원·흥덕·청원) → 선택 구 **요약 카드**(평균 매매 중앙값·전월 등락·전세가율·거래량, tx에서 직접 계산해 표시와 일치) → **단지 리스트**(거래 많은 순 기본, 단지명·대표 시세·거래수, 탭 시 상세 시트).
  - 평형·유형·정렬 등 **세부 필터는 ‘상세’로 접어** 기본 비노출. 검색은 한 줄.
  - 서브탭은 **리스트/지도 2개로 축소, 랭킹 제거**(홈과 중복). 지도=기존 HeatTab 유지.
  - 참고용·신고 지연 고지 유지(왜곡 없음). (구 Price/Rank 컴포넌트는 미사용으로 잔존 — 추후 정리)
## v1.48 (2026-06-21)
- **신고가 경신 알림(신규)** — 재방문 엔진 강화. 기존 ‘관심 단지 신규 실거래 N건’ 알림(이미 구현됨)에 더해, 수집된 신규 매매가가 그 단지의 ‘직전까지 최고가’를 넘으면 `type=new_high` 알림 생성(단지당 1건은 신고가 메시지로 격상). 메시지는 사실만: 신고가·직전 최고가(억). 커서 기반 멱등 유지, 로그인 사용자·실거래(비표본·비해제)만. 프런트 알림함이 new_high를 📈 아이콘으로 표시하고 탭하면 단지로 이동.
  - 동작 검증은 실서버에서 `python -m pytest` + 수집 파이프라인(collect) 후 확인 필요(샌드박스는 DB/네트워크 불가).
## v1.47 (2026-06-21)
- **‘이 단지 매물 보러가기’(외부 연결)**: 단지 상세에 외부 매물 검색 링크 추가(네이버 통합검색·네이버 지도, 단지명+구로 검색). 우리 약점인 ‘실제 매물·마지막 한 걸음’을 운영 부담 없이 보완. 딥링크는 단지 내부ID가 필요해 이름만으론 부정확 → 항상 동작하는 검색 URL 사용. ‘외부 사이트·중개/광고 무관’ 고지 포함(객관성·비제휴).
## v1.46 (2026-06-21)
- **거래 동향 배지(신규)**: 단지 상세 면적별 섹션 앞에 ‘거래 활발/보통/한산’ 표시. 최근 3개월 매매 신고 건수를 직전 3개월과 비교(활발=늘고 1.3배↑·한산=0.7배↓)해, 가격만으로 알기 어려운 ‘거래를 동반한 변화’를 참고로 제공. 색은 가격 방향(빨강/파랑)과 구분되게 TEAL/회색 사용. 표본 적으면 미표시·참고용 고지.
## v1.45 (2026-06-21)
- **적정가 체크(신규)**: 면적별 섹션에 매물·호가를 입력하면 그 평형의 최근 실거래 분포에서 위치를 진단. 중앙값 대비 %, 저점~중앙~고점 범위 막대 + 입력가 마커, ‘최근 N건 중 이 가격보다 낮은 거래 K건(하위 P%)’, 저렴/시세/비싼 판정과 신고가·급매 주의. 백엔드 면적 객체에 거래 분포 `amounts` 노출(공개 실거래값). 참고용·표본 적음 고지 포함(왜곡 없음).
## v1.44 (2026-06-21)
- **내 예산 맞춤 추천도 바닥 시트로 표출**. 홈에는 진입 카드(💰)만 두고, 누르면 `BudgetSheet`(93vh)에 입력·필터·추천 결과를 전부 인라인으로 표출. 기존 ‘N곳 보기→중첩 시트’ 제거(시트 안에서 바로 목록). 상세·통근·예산 모두 동일 시트 패턴으로 통일. `BudgetPicks`에 `embedded` 옵션 추가(제목 중복 제거).
## v1.43 (2026-06-21)
- **통근권도 바닥 시트로 표출**. 전체화면 통근 화면을 없애고 `CommuteSheet`(93vh 바닥 시트)에 통근 검색·결과·지도를 그대로 담음. 결과 탭 → 통근분 요약 시트 → ‘상세 보기’ 시 단지 상세 시트로 연결(상세 시트가 위에 표시). 상세·통근 모두 동일한 시트 패턴으로 통일.
## v1.42 (2026-06-21)
- **단지 상세를 바닥 시트에 전체 표출**(요약→상세 분리 제거). 별도 전체화면 상세 페이지를 없애고, 단지를 누르면 `DetailSheet`(93vh 바닥 시트)에 상세 내용 전부를 그대로 펼침. 시트 안에서 다른 단지를 누르면 같은 시트가 그 단지로 갱신(스크롤 상단으로 리셋).
- 요약 전용 시트(ComplexQuickSheet) 단계 폐지. 통근 결과는 통근분 요약 시트 → ‘상세 보기’ 시 동일 상세 시트로 연결.
## v1.41 (2026-06-21)
- **모든 단지 탭 → 공통 요약 시트로 통일**. 전역 `ComplexQuickSheet` 신설: 단지를 누르면 어디서든(홈 목록·검색결과·순위·급상승/대장·최고상승하락·관심/최근·예산추천) 동일한 바닥 시트로 **대표 시세·전세가율·거래건수·실거래 범위** 요약을 보여주고, ‘전체 상세 페이지 보기 →’로 이동.
  - `openComplex`(요약 시트) / `openDetail`(전체 상세) 분리. 상세 화면 내부 이동·통근 결과는 상세로 직행(통근은 통근분 포함 자체 요약 시트 유지).
## v1.40 (2026-06-21)
- **바닥 시트(팝업) 패턴으로 리스트 표출 통일**(레퍼런스 ‘지금인기/순위’ 방식).
  - 공통 `Sheet` 컴포넌트 신설(딤 배경·480px 중앙·드래그 핸들·헤더·스크롤, body 포털). `RankSheet`가 이를 재사용.
  - **내 예산 맞춤 추천**: 인라인 긴 목록 → ‘추천 단지 N곳 보기 ›’ 버튼 → 시트로 표출. 필터(유형·지역)는 카드에 유지.
  - **통근권 결과 클릭**: 곧장 상세로 가지 않고 **요약 시트**(통근 분·시세·지역·유형 + ‘단지 상세 보기 →’)로 표출.
## v1.39 (2026-06-21)
- **홈 카드 간격 정리**: 커스텀 카드(예산 추천·최고 상승하락·통근 CTA)가 marginTop 2px라 Collapsible(12px)과 간격이 들쭉날쭉하던 문제 → **12px로 통일**.
## v1.38 (2026-06-21)
- **최고 상승·하락: 정렬 추가** — 변동률(%)/변동액(억·만) 토글. 싼 소형 단지의 % 과장 왜곡을 변동액 정렬로 보완.
- **전체화면 오버레이 중앙 정렬 고정** — 검색 화면·순위 시트·약관 모달을 480px 모바일 폭으로 가운데 정렬(넓은 화면에서 풀폭으로 퍼지던 문제 해결).
- **홈 추천 통합** — 별도 '맞춤 추천(관심 지역 기반)' 제거하고, **'내 예산 맞춤 추천'에 지역 필터**(전체/★관심지역/상당·서원·흥덕·청원) 추가. 예산·유형·지역을 한 곳에서. 백엔드 `affordable_complexes`에 `lawd_cds`(구 필터) 추가.
## v1.37 (2026-06-21)
- **홈 ‘구별 매매 추이’ 그래프 제거** → 그 자리에 **‘최고 상승·하락 아파트’** 추가.
  - `stats.top_movers`: 같은 단지·평형에서 **직전 거래 대비** 실거래가가 가장 많이 오른/내린 순위(최근 2건 비교). board에 `top_movers` 포함.
  - 프런트 `TopMovers`: 상승/하락 토글 + 순위 + 단지·평 + 지역 + 변동액(±, 억/만)·변동률(%) + 이전가›현재가. 집계기준 ⓘ(직전 거래 비교·참고용·이상치 가능) 표기. 금액 포맷 `manKor`(억/만, 부호) 추가. 데모 반영.
## v1.36 (2026-06-21)
- **레이아웃 폭 고정(모바일)**: 콘텐츠 컨테이너 `max-width` 1040px(데스크톱) → **480px(모바일, 가운데 정렬)**. 넓은 화면에서 UI가 늘어났다 줄었다 하던 문제 해소 — 폰·모바일웹·데스크톱에서 동일한 폭으로 표시. (하단 네비도 동일 폭)
## v1.35 (2026-06-21)
- **헤더 검색창 축소**: 풀폭 → 우측 정렬 약 200px(절반 이하)로 줄이고 안내문구 간소화('단지·지역 검색').
- **버그 수정: 거래 급상승/대장 배너 클릭 시 순위 시트가 카드 안에 갇혀 잘리던 문제**. 시트를 `ReactDOM.createPortal`로 body에 렌더해 화면 하단 시트로 정상 노출(카드 `overflow:hidden`/transform 영향 제거).
## v1.34 (2026-06-21)
- **헤더 개편 + 검색 화면 강화**(레퍼런스 반영).
  - 헤더에 **작은 검색 pill**을 올림(모든 탭 공통). 누르면 전체 검색 화면(SearchOverlay)이 뜸. 본문에 있던 큰 인라인 검색창 제거.
  - 검색 화면 빈 상태에 **최근 본 단지** + **인기 순위(단지=🔥거래 급상승 / 지역=구별 평단가)** 추가. 메달(🥇🥈🥉)·지역·집계기준 ⓘ 표기(왜곡 없음).
  - **평수(평/㎡)·다크모드·새로고침·계정**을 헤더 **☰ 설정 메뉴**로 통합 → 헤더 간결화. (평수·다크모드 위치 추천 반영)
## v1.33 (2026-06-21)
- **랭킹 배너 → 바닥 시트(모달)로 전환**. 거래 급상승·대장 아파트 배너를 누르면 인라인으로 펼쳐 아래를 밀어내지 않고, **하단에서 올라오는 시트**(딤 배경)로 전체 순위를 보여줌(레퍼런스 UX 반영).
  - 시트: 🥇🥈🥉 메달(1~3위) + 순위 + 단지명 + 지역(시·구·동) + 지표(▲거래건수/대표가). 헤더에 ‘집계기준 ⓘ’로 산정 방식 설명(왜곡 없음). 항목 탭 → 단지 상세.
  - 거래 급상승 결과에 동(dong) 추가로 지역 표기 강화.
## v1.32 (2026-06-21)
- **홈 상단 롤링 배너 2종 추가**(경쟁 앱 '인기 급상승' 형태 차용, 정직한 신호로 구현).
  - **🔥 거래 급상승**: 최근 90일 거래량이 직전 90일 대비 늘어난 단지(`stats.trending_complexes`). 조회수·관심수 같은 미검증 사용자 데이터는 쓰지 않고 ▲N건으로 표기(왜곡 없음). 급상승 표본 부족 시 '거래 활발'(최근 거래량 순)로 폴백.
  - **👑 대장 아파트**: 기존 대표가 중앙값 TOP을 같은 배너 형태로. (기존 큰 카드형 LandmarkCarousel은 제거하고 배너로 통합)
  - 공통 `TickerBanner`: 자동 롤링(3.5s) + 탭하면 전체 순위 펼침, 항목 탭 → 단지 상세. 백엔드 board에 `trending` 포함, 데모도 반영.
## v1.31 (2026-06-21)
- **신규: 홈 ‘내 예산 맞춤 추천’(자본별 매물 추천)** — 대출 계산에서 분리한 독립 커스텀 기능.
  - 홈 상단에 배치. 보유 현금(필수)·연소득(선택, 동의 시) 입력 → **이 기기에만 저장(서버 전송·저장 없음)**, 다음 방문부터 자동 활용.
  - 예산(자기자본+대출) 산출 → 그 이하 단지를 ‘자기자본+대출·월상환·시세’와 함께 추천. **전 유형(아파트·오피스텔·빌라·단독) 기본 + 유형 필터**. 표본 적음·비아파트 개략 라벨로 왜곡 방지.
  - 백엔드 `affordable_complexes`: 전 유형 지원(`property_type='all'`/None) + 결과에 `property_type` 포함.
  - 기존 대출 상세의 ‘이 예산으로 살 수 있는 단지’ 블록은 제거(중복 해소). 단지별 적정성은 상세의 ‘실구매력 진단’이 계속 담당.
## v1.30 (2026-06-21)
- **시세 탭 검색바 중복 정리**. 상단 전역 검색바를 시세 탭에서는 숨김(홈·청약·매물·게시판엔 유지). 시세 탭은 유형·구·평형·정렬과 묶인 자체 목록 검색 하나만 노출 → 탭당 검색창 1개로 깔끔.
## v1.29 (2026-06-21)
- **통근권 지도 뷰 추가**. 통근 검색 화면에 리스트/지도 토글.
  - 지도: **목적지 마커(🏢)** + 결과 단지 마커(통근 분 표시, 시간대별 색: ≤15 초록·≤30 청록·≤45 주황·45+ 빨강). 핀 클릭 → 하단 시트(단지명·구·유형·분·시세 + ‘단지 상세 →’). 결과 범위에 맞춰 자동 fitBounds.
  - 백엔드 `commute` 응답에 목적지/단지 좌표(lat/lng) 노출, 데모 결과에도 좌표 포함(미리보기 동작). 좌표 없으면 안내(왜곡 없음).
## v1.28 (2026-06-21)
- **차별화 ③ 적정가/실구매력 진단**. 대출 계산에 ‘이 단지가 내 예산에 적정/빠듯/무리’ 판정 추가(매수 의사결정 도움).
  - 백엔드 `loan._affordability`: 필요 대출이 LTV·DSR 한도 안인지 + 월 상환액의 소득 대비 **부담률**로 4단계 판정(적정 ≤25% · 빠듯 25~35% · 부담 큼 35%↑ · 무리=한도초과/현금부족). `estimate` 반환에 `affordability` 포함.
  - 프런트 `AffordVerdict` 카드: 판정 배지 + 월 예상 상환 + 부담률(+필요대출), 상황별 코멘트(한도 부족/현금 부족/부담률). 데모 `loanLocal`도 동일 로직 반영.
  - 기존 대출 동의(ConsentGate)·미저장(stateless) 흐름 재사용 — 민감정보(소득) 입력은 맞춤 모드에서만, 저장 안 함(9.A 준수).
## v1.27 (2026-06-21)
- **차별화 ② 통근권 — 프런트 + 검색 화면**. 홈에 ‘🧭 통근권으로 집 찾기’ 진입 카드 → 전용 검색 화면.
  - 목적지 선택(교통/직장/공공/교육 칩) → 수단(자동차/대중교통) → 유형 → ‘N분 이내’ 슬라이더 → **시간순 단지 리스트**(분 배지 + 구·유형 + 최근 중앙 매매가, 추정/실측 라벨). 단지 탭 → 시세 상세.
  - 백엔드 `search_by_commute`에 결과별 `lawd_cd`·`price`(최근 N개월 중앙 매매가) 결합 → ‘시간 + 가격’ 동시 판단.
  - 데모: 청주 4개 목적지 + 단지 좌표로 즉석 haversine 추정(미리보기 동작). ‘추정(직선거리)’ 라벨로 왜곡 없이 표기.
## v1.26 (2026-06-21)
- **차별화 ② 통근권 — 데이터/백엔드 토대**(설계 우선, 운영·확장 고려). 프런트는 후속.
  - 모델: `CommuteDestination`(운영자 관리 목적지) + `CommuteTime`((단지×목적지×수단) 통근시간 캐시, 'N분 이내' 인덱스). 마이그레이션 `0009_commute`(create_table·inspect 가드·portable).
  - 서비스 `services/commute.py`: 카카오모빌리티 길찾기 실측(`api`) 또는 직선거리 추정(`haversine`) — 정확도 라벨로 구분(왜곡 없음). 캐시 우선 + 콜드스타트 즉석 추정.
  - 시드 `app/data/commute_seed.py`(청주 8개 거점: 오송역/오송바이오/오창산단/시청/도청/공항/터미널/충북대, 좌표 seed_approx). 스크립트 `scripts/seed_commute.py`(+--geocode), `scripts/compute_commute.py`(증분 배치).
  - API: `GET /commute/destinations`, `GET /commute/search?dest_id=&mode=&max_minutes=&property_type=`. 설정값(평균속도·우회계수·TTL) 분리.
  - DATA.md/OPERATIONS.md 운영 절차 + `tests/test_commute.py`.
## v1.25 (2026-06-21)
- **단지 상세: ‘전세 안전도’ 섹션을 대출 계산 바로 아래로 이동**. 매매 상세의 매수자 흐름(가격 → 면적별 상세 → 대출 계산 → 전세 안전도)에 맞게 재배치. 상단은 가격·신뢰 정보에 집중.
## v1.24 (2026-06-21)
- **차별화 ① 실거래 신뢰 필터** (시세 왜곡 줄이기 — ‘왜곡 없음’ 강화). 다른 부동산 앱이 약한 지점.
  - 데이터층: `transactions.trade_method`(거래유형 중개/직거래) 컬럼 추가 + MOLIT `dealingGbn/거래유형` 파싱(`agent`/`direct`/null). 마이그레이션 `0008_tx_trade_method`(nullable·inspect 가드·portable). 정정 경로에서도 trade_method 갱신.
  - 통계층: `complex_detail`/`_area_block`이 거래행마다 **정정(corrected)·직거래(direct)·이상치(outlier)** 플래그 제공(이상치=같은 평형 중앙 평단가 대비 ±30% 초과, `stats._tx_out`). 단지·평형 **표본 신뢰도**(`reliability`: low/fair/ok), **해제 건수**(`canceled_count`) 노출.
  - 프런트: 최근 실거래 행에 정정/직거래/이상치 배지(이상치는 취소선). ‘표본 적음’ 표시. 단지 상단에 ‘해제 N건 제외 · 표본 적음’ 안내(callout).
  - 데모/문서/테스트: demoDetail에 4개 신호 반영(미리보기 시연), DATA.md 운영 메모, `tests/test_trust.py` 추가. 시세 리스트도 해제분 제외.
## v1.23 (2026-06-20)
- **공유용 시세 카드 (바이럴 성장 기능)**. 단지 상세 하단 ‘📤 이 시세 카드 공유하기’ 버튼 → 단지 시세를 예쁜 카드 이미지로 생성.
  - 외부 라이브러리 없이 **Canvas 2D로 직접 렌더**(오프라인 동작): 단지명·구/동/유형/연식, 최근 매매가+전고점 대비, 중앙값·평단가·거래건수, 전세 안전도 게이지, 최근 N개월 추이 미니차트, 출처/참고용 고지.
  - **이미지 저장**(PNG 다운로드) + **공유하기**(Web Share API — 카톡 등 네이티브 공유 시트; 미지원 환경은 저장 후 첨부 안내).
  - 평형을 좁혀 본 경우 그 평형 기준, 전체 보기면 단지 전체 기준 카드. 모의 데이터는 ‘모의’ 배지 표기(왜곡 방지).
  - 참고: 아티팩트 미리보기 iframe에선 저장/공유가 제한될 수 있고, 실제 배포 앱·모바일에서 정상 동작.
## v1.22 (2026-06-20)
- **단지 상세: ‘전세 안전도(깡통전세 위험)’ 진단 섹션 추가**. 기존 전세가율 데이터 기반(새 API 없음, 왜곡 없음).
  - 4단계 게이지: ~70% 안전한 편 · 70~80% 보통 · 80~90% 주의 · 90%~ 위험(깡통 우려). 현재 전세가율 위치 마커 표시.
  - 단계별 코멘트 + ‘계약 전 확인’ 체크리스트(선순위 채권·근저당, 임대인 세금 체납, 반환보증 가입, 확정일자·전입신고).
  - 보증금 반환보증 안내: HUG(khug.or.kr)·HF(hf.go.kr)·SGI. ‘참고 지표일 뿐, 법률·금융 자문 아님’ 고지 포함.
  - 평형을 좁혀 본 경우 해당 평형 전세가율 기준, 전체 보기일 땐 단지 전체 기준으로 표기.
## v1.21 (2026-06-20)
- **단지 상세: 클릭한 평형만 표시**. 리스트/그룹에서 특정 거래(특정 전용면적)를 누르면, 그 단지의 '같은 평형'만 보이도록 변경(이전엔 단지의 모든 평형이 함께 표출).
  - 클릭 시 `exclusive_area`를 상세로 전달(`sel.area`). 상세에서 전용면적을 평(3.3㎡)으로 반올림해 같은 평형대만 필터(예: 84.9㎡·85㎡ → 둘 다 26평이라 함께, 101.2㎡(31평)는 분리).
  - 좁혀진 경우 상단에 '전용 OO㎡ 평형만 보는 중 · [전체 평형 보기]' 배너 노출. 버튼으로 전 평형 보기로 전환.
  - 대출 계산의 면적 토글·자동입력도 해당 평형 기준으로 한정. 평형 전환 시 대출 선택 초기화.
  - 면적 정보가 없는 진입(검색·관심·최근·대장아파트·지도 핀·'단지 상세 보기')은 기존대로 전체 평형 표시.
## v1.20 (2026-06-20)
- **버그 수정: 단지 상세가 안 뜨던 문제(데모/standalone 화면)**. 데모 폴백 함수 `demoDetail`이 정의되지 않은 변수(`trough`·`amts`·`pmed`·`jrate`·`fb`·`recent`)를 참조해 런타임 오류로 throw → Detail이 스켈레톤(로딩) 상태에서 멈춰 상세가 표시되지 않았음. 누락 변수를 백엔드와 동일한 의미(저점·중앙값·전세가율·최근거래 등)로 정의해 해결. (실서버 경로는 영향 없었음 — 데모 전용 버그)
- node로 demoDetail 회귀 검증 추가 확인(found/median/jeonse_ratio/recent 정상).
## v1.19 (2026-06-20)
- **홈 ‘내 동네’ 삭제**: 홈 상단 구 선택 칩 제거(맞춤 추천은 관심 지역 기반으로 유지).
- **시세 ‘조건 저장’ 삭제**: 저장된 조건 칩 + ‘＋ 이 조건 저장’ 버튼 제거.
- **시세 조건 UI 전면 개편**: 흩어져 있던 조건(유형·구·검색·평형·정렬)을 리스트 상단 **한 장의 카드**로 통합·정돈.
  - 구성: ① 검색창 → ② 유형·구 드롭다운(2열) → ③ 평형 세그먼트 → ④ 정렬 세그먼트 → ⑤ 총 건수 · 관심만 · 초기화.
  - 칩 난립 대신 라벨+세그먼트 컨트롤로 한눈에 보이게. 활성 필터가 있으면 ‘초기화’ 노출.
  - 지도·랭킹 뷰는 유형만 필요하므로 상단에 유형 셀렉터만 간결하게.
## v1.18 (2026-06-20)
시세 탭 UX 6종 (인기 부동산 앱 패턴 반영):
- **① 단지·동 인라인 검색**: 리스트 상단에 검색창. 단지명/법정동 부분일치로 즉시 필터.
- **② 평형(면적) 필터**: 전체/소형(~60㎡)/중형(60~85)/대형(85~) 칩.
- **③ 단지 묶음 카드**: 개별 거래 나열 → 단지별로 묶어 대표가(중앙값)·건수·평단가 표시, 탭하면 개별 거래 펼침 + ‘단지 상세 보기’. (단독·다가구는 개별 행 유지)
- **④ 평단가순 정렬**: 가격순/평단가순/최신순. 정렬값이 단지 그룹 순서까지 반영.
- **⑤ 지도 핀 → 하단 시트**: 단지 핀 클릭 시 화면 전환 대신 지도 위 하단 카드로 대표 평단가·건수 미리보기 + 상세 이동. (구 핀은 기존대로 구 드릴다운)
- **⑥ 관심만 보기**: 관심 등록 단지가 있으면 ‘★ 관심만’ 토글로 리스트를 관심 단지로 한정.
- favs를 App→PriceHub→Price로 전달. 거래행 마크업을 TxRow 컴포넌트로 분리(재사용).
## v1.17 (2026-06-20)
- **시세 탭: 유형 + 구 필터를 상단에 함께**: 그동안 유형은 상단 공유 바, 구는 리스트 내부에 떨어져 있던 것을 합침. 리스트 뷰에서 상단 바에 [유형][구]가 나란히 노출되어 한 번에 조건 설정. (지도·랭킹 뷰에선 구 필터 숨김 — 전체 개요라서)
- **소식 탭 제거 → 홈 '오늘의 정보'로 통합**: 하단 탭을 6→5개(홈·시세·청약·매물·게시판)로 축소. 부동산 뉴스·정책·지원 목록을 홈 '오늘의 정보' 영역(청약 임박 + 뉴스 + 정책 collapsible)으로 이동. 정책은 기본 접힘.
## v1.16 (2026-06-20)
- **홈 '구별 매매가 랭킹' 섹션 삭제**(시세 탭 랭킹과 중복). 관련 미사용 변수(gus/maxpp/sortMine) 정리.
- **대장아파트 클릭 시 상세가 비던 문제 보강**: `complex_detail`이 유형(property_type) 힌트로 0건이면 유형을 무시하고 `name+lawd_cd`로 재조회하도록 폴백 추가(잘못된 유형 힌트에도 단지를 찾음). 캐러셀 클릭 시 gu·dong도 함께 전달.
## v1.15 (2026-06-20)
- **홈 '오늘의 정보' 위젯 추가(실용 정보)**: 홈 하단에 ① 청약 임박(접수중>접수예정 우선 1건, 상태 배지·기간·위치, 탭 시 청약 탭) ② 최신 뉴스 1건(출처·일자, 링크/뉴스 탭) + '청약 전체'·'뉴스·정책' 바로가기. 청약은 /subscription 직접 조회(실패 시 예시 폴백), 뉴스는 기존 feed 재사용. 앞서 제안한 홈 5블록 구성 완성.
## v1.14 (2026-06-20)
- **홈 '대장아파트' → 자동 슬라이드 배너(캐러셀)**: 평형(소·중·대형) 구분을 없애고 단지 대표가 중앙값 기준 **TOP 5**만 노출. 3.5초마다 자동 전환, 마우스오버·터치 시 일시정지, 하단 점(dots)으로 이동, 카드 탭 시 단지 상세. 백엔드가 이미 내려주던 평면 `landmark`(top5) 사용.
## v1.13 (2026-06-20)
- **시세 탭 통합 — 유형(매물종류)을 전 뷰 공통 컨트롤로 승격**: 그동안 리스트/지도/랭킹이 각자 유형 셀렉터를 따로 가져 뷰 전환 시 맥락이 끊겼음. PriceHub 상단에 공유 '유형' 컨트롤을 두고 리스트·지도·랭킹에 모두 반영(유형 변경 시 랭킹 데이터도 자동 재요청). '전체 유형'은 리스트에서 지원, 지도·랭킹은 아파트 기준으로 안내 표기.
  - 전략: 시세 탭 = '쌓기'가 아니라 '상단 컨트롤(유형 공유) → 뷰 토글(한 번에 하나) → 구·동·단지 드릴다운'의 탐색 도구. 길이 증가 없이 일관성 확보.
  - 각 뷰 고유 컨트롤은 유지: 리스트(구·정렬·거래유형), 지도(구/단지 단위), 랭킹(지표).

## v1.12 (2026-06-20)
- **홈 화면 재구성(간결화 + 핵심 보완)**:
  - **추가**: 최상단에 '청주 아파트 시세 요약 히어로'(평균 매매/전세 + 전월·전년 등락 + 기준월). 그동안 백엔드 city_summary 가 계산되지만 홈에 미표시였던 핵심 누락을 보완. `/dashboard/board` 응답에 `city` 추가.
  - **정리(중복 제거)**: 시세 탭과 겹치던 '구별 최신 실거래' 섹션 제거, '구별 매매 추이'는 기본 접힘, '구별 매매가 랭킹' 하단에 '시세에서 더보기(지도·최신 실거래)' 버튼 추가 → 전체 탐색은 시세 탭으로 유도.
  - 결과: 펼친 섹션 8개 → (히어로 + 관심/최근/내 동네 + 맞춤추천 + 대장 + 랭킹) 중심으로 축약. 개인화·정직성 배지 유지.
  - 오프라인 데모(demoBoard)에도 city 샘플 추가.

## v1.11 (2026-06-20)
- **집계 기본 윈도우 = 최근 12개월** (`.env` `aggregate_months`, 기본 12). 현재 시세(중앙값·평단가·전세가율·거래량·랭킹·지도·비교·예산매칭)는 최근 12개월 실거래만 사용.
  - `stats._load`(최근 N개월) / `_load_all`(전체) 분리. 전년대비(YoY)·단지 다년 추이만 `_load_all`.
  - 단지 상세 '고점/저점 대비'도 최근 N개월 기준으로 라벨 정정.
  - **화면 표기**: /config 의 `aggregate_months` → 프런트 `AGG_MONTHS`. 푸터·단지상세·비교·예산매칭에 "최근 N개월 실거래 기준" 노출.
  - 테스트 test_stats.test_aggregate_window_excludes_old. DATA.md·aggregations 스킬 갱신.
- 참고: 중앙값(median)은 의도적 선택 — 실거래가의 이상치(고가·증여성 저가)에 강건해 대표 시세로 평균보다 적합.

## v1.10 (2026-06-20)
- **운영자용 데이터 설명서 추가(DATA.md)**: 저장 환경, 공통 규칙(만원 단위·is_sample·is_canceled·source·raw_payload), 핵심 테이블(regions/complexes/transactions) 컬럼 상세, 매물·커뮤니티·개인화 테이블 요약, 데이터 흐름(수집→정규화→적재→집계), 집계 기간 기준, 보존·파기, 개인정보, **PostgreSQL 테이블·데이터 확인 방법(psql/pgAdmin/SQL 예시)** 정리. README·OPERATIONS 에서 링크.

## v1.9 (2026-06-20)
- **버그픽스(PostgreSQL 마이그레이션 이식성)**: SQLite 기준으로 작성돼 PG 에서 깨지던 부분 수정. 전 마이그레이션·스키마 경로 전수 점검.
  - `migrations/0003_tx_cancel`: `UPDATE ... is_canceled = 0` → `= false`(PG 는 boolean 에 정수 미허용). **이번 에러의 직접 원인.**
  - `db/session.init_db`: PostgreSQL 에서는 `create_all`/`_ensure_columns` 를 호출하지 않음 → 스키마는 Alembic 단일 권위. (create_all↔migration 충돌·raw DDL 위험 제거)
  - `db/session._ensure_columns`: 비-SQLite 에서 즉시 반환(raw DDL `DATETIME`·`=0` 는 SQLite 전용).
  - 점검 결과: 나머지 마이그레이션(0001·0002 baseline create_all·0003_alerts·0004·0005·0006·0007)은 모두 `inspect` 가드로 멱등·이식성 OK. 앱 쿼리는 ORM 이라 dialect 안전.

## v1.8 (2026-06-20)
- **버그픽스(마이그레이션 DB URL의 % 문자)**: 비밀번호에 `@`(=`%40`)·`%` 가 들어간 `DATABASE_URL` 을 alembic 이 ConfigParser 에 넣다가 `invalid interpolation syntax` 로 죽던 문제 수정.
  - `migrations/env.py`: DB URL 을 ConfigParser 를 거치지 않고 설정에서 직접 읽어 `create_engine` 으로 사용(`%/@` 인코딩 안전, SQLAlchemy 가 정확히 디코딩).
  - `scripts/db_upgrade.py`: `sqlalchemy.url` 을 더 이상 cfg 에 주입하지 않음(미사용 import 정리).

## v1.7 (2026-06-19)
- **버그픽스(Windows 마이그레이션)**: `python/uv -m scripts.db_upgrade` 실행 시 한글 Windows 로케일(cp949)에서 `alembic.ini`의 한글 주석을 못 읽어 `UnicodeDecodeError`가 나던 문제 수정.
  - `alembic.ini`를 ASCII로 정리(주석 영문화).
  - `scripts/db_upgrade.py`가 `alembic.ini`를 직접 읽지 않고 `Config()`를 코드로 구성(script_location·sqlalchemy.url 주입) → 로케일/인코딩과 무관하게 동작.

## v1.6 (2026-06-19)
- **네비 정리(8→6탭)**: '가격을 본다'가 흩어져 있던 시세·랭킹·지도를 **하나의 '시세' 탭**으로 통합(상단 리스트/지도/랭킹 토글). 하단 네비는 홈·시세·청약·매물·게시판·소식 6개로 단순화.
  - PriceHub 래퍼(뷰 토글) + priceView 상태. 기존 Price/HeatTab/Rank 컴포넌트 재사용(로직 변경 없음). 구 선택(goGu)·검색·지도 핀 이동은 리스트 뷰로 자동 전환.

## v1.5 (2026-06-19)
- **예산 기반 단지 매칭("이 예산으로 살 수 있는 단지")**: 보유현금(+소득)으로 살 수 있는 최대 매매가를 산출하고, 그 예산 이하 청주 단지를 시세로 매칭. 단지별 '자기자본 OO + 대출 OO · 월상환 OO' 제공. 대출+시세 결합(우리만의 강점).
  - 백엔드 `loan.max_affordable_price`(estimate의 total_cash_needed 이진탐색 → 대출탭과 일관) + `stats.affordable_complexes` + `POST /loan/affordable`. 테스트 test_affordable.py.
  - 프런트: 대출 화면에 '내 예산으로 단지 찾기' 섹션(예산 헤드라인·단지 카드·탭하면 상세). 금리·기간 기준 참고치 고지.
- **버그픽스**: 단지 상세(Detail)에 v1.3 비교 토글 props(inCompare/onToggleCompare)가 시그니처에 빠져 비교 버튼이 안 뜨던 문제 수정(+ onOpen 추가).

## v1.4 (2026-06-19)
- **청약·분양 정식 탭**: 소식 탭에 섞여 있던 청약을 전용 '청약' 탭으로 분리(하단 네비 추가, 전용 아이콘).
  - 상태 필터 칩(전체/접수중/접수예정/마감, 건수 표시) + 공고 카드(단지·지역·기간·공급세대·분양가·경쟁률·최저가점·주택형별).
  - 백엔드 `GET /subscription`(청약홈 applyhome, 키 없으면 예시 폴백·live 플래그·안내·출처 고지). 테스트 test_subscription.py.
  - 소식 탭은 이제 뉴스·정책만.

## v1.3 (2026-06-19)
- **단지 비교(Compare)**: 최대 4개 단지를 나란히 비교(최근 매매가·평단가·전세가율·전고점 대비·거래량·준공·세대수). 항목별 '최적' 강조(평단가↓·전세가율↓·거래량↑·준공↑, 투자판단 아님 고지). 전세가율은 위험색 반영.
  - 백엔드 `stats.compare_one` + `POST /compare`(최대 4개, 거래 없으면 found=False). 테스트 test_compare.py.
  - 프런트: 단지 상세 '⊕ 비교' 토글 → 하단 플로팅 '비교 N개' 바 → 비교 오버레이(가로 스크롤·지표 고정열·열별 제거). 선택은 기기에 저장(safeStore).

## v1.2 (2026-06-19)
- **전세가율 위험 배지(깡통전세 안내)**: 전세가율 80%↑ '높음'·90%↑ '매우 높음' 배지+툴팁(데이터 기준·단정 아님). 안전 조회 트렌드 반영.
- **대출 안내 강화**: '회원가입·신용조회 없이 한도 미리보기(구간만 사용·조회기록 없음)' 배너. 기존 공시 면책·실시간 공시 배지 유지.
- **검색 인덱스(pg_trgm)**: PostgreSQL 부분일치 LIKE 가속 GIN 인덱스 마이그레이션 0007(타 DB는 건너뜀).
- **초기 로딩 최적화**: 홈 첫 로드 랭킹 limit 300→60(랭킹 탭은 자체 조회).
- **정리**: 미사용 `price_per_m2`(샘플) 제거, 미사용 `by_area`(단지상세) 제거, 지도 로더 스켈레톤화, 콜아웃 다크모드 토큰화(--callout-*).

## v1.1 (2026-06-19)
- **단지 데이터 보강(K-apt)**: 세대수·동수·사용승인일(연식)·난방·연면적·시공사·주차. 미설정/미매칭은 null(날조 금지). `scripts/enrich.py`·`/admin/enrich`.
- **실거래 정정·해제 반영(⑥)**: 정정=기존 행 갱신(중복 없음)·해제=집계 제외·멱등·모호 보존. 정정/해제 건수를 `/status/data`에 노출. 회귀 테스트 추가.
- **공시가격 보강**: 공식 CSV(호별)→단지·면적 중앙값 집계 임포터(`scripts/import_gongsi.py`). 청주 한정·매칭 실패 null.
- **학군(통학 접근성)**: 카카오 POI(학교)로 인근 학교 수·최단·초/중/고. 거리 기준(학업성취 아님) 명시.
- **외부 API 엔드포인트 .env화**: MOLIT·네이버/카카오·finlife·청약·뉴스·OAuth·K-apt 주소를 모두 설정값으로(빈 값이면 코드 기본값).
- **운영 가이드 OPERATIONS.md**: 설치·운영·배포·모니터링·장애대응·점검 체크리스트.
- **UI 개편**: 시세 면적별 카드 분리(+면적 미상)·모바일 행 카드·필터 고정·로딩 스켈레톤·단지 미니 스파크라인·단위 툴팁·접힘 애니메이션·터치영역·빈 상태 통일·**다크 모드**.
- **마이그레이션 체인 정리**(0001→…→0006 단일 head).

## v1.0 (기준선)
- 초기 MVP: 실거래 수집·정규화 파이프라인, 시세/대시보드/검색/단지상세/비교, 청약·뉴스, 대출 추천(동의·간이모드), 커뮤니티, 지도/POI, 알림(이메일·푸시·알림톡 토대), 인증, 관측성·레이트리밋·법적 고지·테스트/CI.
