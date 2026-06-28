# TESTING — 테스트·검증 방법 (전 레이어 기록)

> 이 프로젝트를 어떻게 테스트/검증하는지 **한곳에 기록**합니다. 인수인계·릴리스 전 점검의 단일 출처.
> 원칙: 왜곡 없음 · 무엇을 어디서(샌드박스/개발 머신/실기기) 돌리는지 명시 · 통과 기준 명확.

## 0. 어디서 무엇을 도는가 (중요)
| 환경 | 가능 | 불가 |
|---|---|---|
| 코드 작성 샌드박스(네트워크 X) | Python 컴파일·pytset(외부키 없음)·**오프라인 무결성 검증**·diff | `npm install/build`·`pip install`·`uvicorn` 실행·네이티브 빌드 |
| 개발 PC(Node+Python) | 위 전부 + **프런트 빌드/실행·PWA·백엔드 실행·실데이터 수집** | iOS 네이티브 빌드(Mac 필요) |
| 실기기/에뮬레이터 | Android 셸·푸시 수신·세이프에어리어 | — |
| macOS + Xcode | iOS 셸·TestFlight | — |

---

## A. 백엔드 / 실데이터 (개발 PC)
실거래가 화면에 나오려면 **키 + 수집**이 둘 다 필요합니다.
```
python -m scripts.doctor              # 빠진 설정/키/데이터 한눈에 (❌부터 해결)
python -m scripts.verify_region_codes # 지역코드·serviceKey(인코딩/디코딩)·401·활용신청 정밀 진단
python -m scripts.run_collect live    # 실수집(키 필요). 'fixtures'=모의데이터(키 0)
```
브라우저 확인:
- `http://localhost:8000/health` → `ok`(db_ok·데이터 신선도)
- `http://localhost:8000/status/data` → 최신 계약일·구별 커버리지·마지막 수집(비면 미수집)
- 화면 상단 배너: "백엔드 연결됨 · 실거래" / "모의데이터 포함" / "미응답" 구분
**통과 기준**: status/data에 4개 구 계약일·건수가 채워지고, 배너가 "실거래 데이터".

## B. 백엔드 회귀 테스트 (개발 PC / 샌드박스 일부)
```
pip install -r requirements.txt
pytest                                # 대출·세금·정규화·집계캐시·원자카운터·알림·API 스모크
```
- 버리는 SQLite + 외부키 비움(네트워크 차단)으로 격리. push/PR마다 GitHub Actions(CI) 자동 실행.
- 백엔드 파일 수정 시: `python -m compileall app` 로 컴파일 먼저.
**통과 기준**: 전부 green. 새 기능/버그수정엔 테스트 동반.

## C. 오프라인 코드 검증 (네트워크 0 — 샌드박스/PC 공통)
### C-1. 프런트 추출 무결성 (Phase A/B)
```
python -m scripts.verify_frontend
```
- frontend/src/main.jsx 본문이 레거시 app/web/index.html과 **API 1줄만 다름** + 괄호 균형 + React/ReactDOM import 커버 + index.html(CDN 제거·module·root·manifest·SW) 확인.
**통과 기준**: `PASS ✅`, 종료코드 0.

### C-2. 레거시 프런트 수정 시 (app/web/index.html 직접 손볼 때)
CLAUDE.md §6 스니펫 — babel 스크립트 괄호 균형 + 미정의 컴포넌트 스캔(둘 다 0).

## D. 프런트 빌드 (Phase A — 개발 PC, Node 18+)
```
cd frontend
npm install
npm run build        # 에러 0 → dist/ 생성
npm run preview      # 빌드 결과 로컬 서빙
# (개발 중 HMR) npm run dev → http://localhost:5173
```
**UI 체크리스트(원본과 동일해야)** — preview/dev에서 직접:
- [ ] 탭 전부 렌더·동작: 홈 · 시세 · 청약 · 매물 · 게시판 (+ 단지상세·지도·뉴스·대출·관심·로그인)
- [ ] 지도(네이버 SDK 런타임 주입) 표시
- [ ] 모달/바텀시트·차트·공유 QR(=createPortal 사용처) 정상
- [ ] 백엔드 끄면 **데모 폴백**(예시 배지)로 화면 유지
- [ ] 콘솔 에러 0
- [ ] (더보기) 매물·청약·단지상세 최근거래·시세 거래그룹이 처음 일부만 보이고 **더보기(남은 N개)**로 증분 로드 — 길이·렌더 부담 감소
- [ ] (에러바운더리) 강제로 컴포넌트에서 throw 시 **백스크린이 아니라 "일시적인 오류" 카드 + 새로고침** 노출(정상 동작 시엔 변화 없음)
**통과 기준**: 위 전부 + 빌드 에러 0. (백엔드 연동은 `.env.development`의 VITE_API_BASE)

## E. PWA / 설치형 (Phase B — 개발 PC, 크롬)
> `localhost`는 보안 출처로 취급 → HTTPS 없이 테스트 가능.
- 크롬 **DevTools → Application**:
  - [ ] Manifest: 이름·아이콘(192/512/maskable)·theme_color 인식
  - [ ] Service Workers: `/sw.js` 등록·activated
- [ ] 주소창 **설치 아이콘** → "앱 설치" → 독립창(standalone) 실행
- [ ] 모바일 크롬/사파리에서 "홈 화면에 추가" → 주소창 없는 실행
**통과 기준**: 설치 가능 + 매니페스트/SW 정상.

## E-2. 컷오버 (레거시 → dist 서빙) — 개발 PC, 런타임
> 절차·롤백 전체는 `CUTOVER.md`. 백엔드가 `frontend/dist`를 서빙하도록 전환했을 때 확인.
```
cd frontend && npm run build
cd .. && export WEB_DIR="$(pwd)/frontend/dist" && uvicorn app.main:app --port 8000
```
- [ ] `/` 새 빌드 화면 / DevTools Network: `/assets/*`·`/manifest.webmanifest`·`/icons/*` 200
- [ ] API 안 가려짐: `/health`·`/config`·`/transactions` 정상 / `/sw.js` 200
- [ ] 모든 탭·기능 레거시와 동일 / 콘솔 에러 0
- [ ] 롤백: `unset WEB_DIR` → 재시작 → 레거시 복귀
**통과 기준**: 위 전부. (샌드박스에선 문법·전환 로직만 확인됨 — 런타임은 여기서)

## F. Capacitor / Android (Phase C — 개발 PC + Android Studio)
> 런북: `frontend/CAPACITOR.md`. 선행: D(빌드) 통과.
```
# (CAPACITOR.md 순서) cap add android → .env.production 채우고 npm run build → npx cap sync → npx cap open android
```
실기기/에뮬레이터에서:
- [ ] 앱 실행·핵심 화면 동작(홈/시세/단지/뉴스/대출/청약/게시판/관심/로그인)
- [ ] API 연동(VITE_API_BASE 절대 URL) — 백엔드 CORS 허용 확인
- [ ] 상태바/노치 겹침 없음(세이프에어리어 CSS 적용 후)
- [ ] 외부 링크는 시스템 브라우저, 뒤로가기 정상
**통과 기준**: 위 전부 + 빌드/실행 에러 0.

## G. Phase D 예정 (네이티브 푸시 + iOS — 기록 자리)
- 네이티브 푸시(FCM/APNs): 토큰 등록 → 서버 발송 → 수신·클릭 딥링크. (웹푸시 VAPID는 PWA용 유지)
- iOS: **macOS + Xcode** → TestFlight 내부 테스트. (작성 시 이 절 채울 것)

---

## 릴리스 전 체크리스트 (매 전달 시)
1. `python -m compileall app` (백엔드 무손상)
2. `pytest` (회귀 green)
3. `python -m scripts.verify_frontend` (프런트 무결성 PASS)
4. 레거시/백엔드/`main.jsx` 본문 무변경 의도 확인(비파괴 작업 시 diff)
5. `VERSION`·`CHANGELOG.md` 갱신, 산출물 `_vMAJOR_MINOR` 접미사
> 빌드/실기기/심사 항목은 **개발 머신·기기에서** 별도 수행(샌드박스 불가).

## H. 수익화 스캐폴딩(부록B) 테스트 — 전부 플래그 OFF가 기본(현재 동작 불변)
> 목적: 첫 출시엔 제외(OFF) 가능한 구조 검증. 플래그를 켜야만 동작이 나타남.
**기본(OFF) 확인** — 아무 설정 없이:
- [ ] 매물 목록 정렬·표시가 기존과 동일(광고 배지 없음). `/auth/me` 의 `is_premium=false`, `plan="free"`.

**광고/제휴 노출(sponsored) 테스트**:
```
export FEATURE_ADS=true            # 서버 재시작
# 매물 하나를 광고로 표시(관리자 토큰 필요)
curl -X POST "http://localhost:8000/admin/test/sponsor?listing_id=<ID>&on=true&priority=10" -H "X-Admin-Token: <TOKEN>"
```
- [ ] 매물 목록에서 해당 매물이 **상단 + "광고" 배지**(amber)로 노출. FEATURE_ADS 끄면 배지·우선정렬 사라짐(저장값은 유지).

**프리미엄 권한(plan) 테스트**:
```
export FEATURE_MONETIZATION=true   # 서버 재시작
curl -X POST "http://localhost:8000/admin/test/plan?account_id=<ID>&plan=premium" -H "X-Admin-Token: <TOKEN>"
```
- [ ] `/auth/me` 가 `plan="premium"`, `is_premium=true`. FEATURE_MONETIZATION 끄면 `is_premium=false`(게이팅 비활성).
> 현재 어떤 기존 기능도 require_premium 으로 막지 않음(구조만). DB 컬럼은 마이그레이션 `0012_monetization`.

## I. 중개사 대시보드 v2(조회수·상태·수정) 테스트
> 중개사 계정(role=agent) 로그인 → 계정 메뉴 "📊 중개사 대시보드".
- [ ] (요약) 총 매물·활성·**총 조회수**·(FEATURE_ADS 시 광고) 카드, 거래유형/구 분포 표시.
- [ ] (조회수) 다른 사용자가 매물 상세를 열면 조회수 +1, **소유자 본인 조회는 미증가**. (대시보드 목록 로드는 증가 안 함)
- [ ] (상태) "거래완료/판매중" 토글, "숨김/복구" 토글 동작. 숨김·거래완료는 **공개 목록에서 제외**되지만 대시보드(manage)에는 계속 보임.
- [ ] (수정) 매물 "수정" → 전체 폼이 기존 값으로 채워짐 → 값 변경 후 "수정 저장" → 목록 갱신. status/조회수/광고여부는 보존.
- [ ] (권한) 등록자만 수정/상태변경 가능(403). 숨김 매물은 소유자만 상세 조회 가능(타인 404).

## J. 출시 품질(접근성·빈상태·오프라인) 테스트 — v1.90

> 대부분 실제 브라우저/기기에서 확인(샌드박스 렌더 불가).

**접근성(focus-visible)**
- [ ] 키보드 Tab으로 버튼·필터·매물카드 이동 시 **teal 외곽선(2.5px)** 이 보임. 마우스 클릭 시엔 외곽선이 안 떠야 정상(:focus-visible 동작).
- [ ] OS "동작 줄이기(reduce motion)" 켜면 애니메이션·트랜지션이 즉시 끝남.

**키보드 네비게이션(접근성 2차)**
- [ ] Tab으로 매물카드·게시글카드·임장 단지·홈 배너(거래급상승/대장/최근 본 단지)·랭킹/최근 시트 행에 포커스 이동 → Enter/Space로 열림(클릭과 동일).
- [ ] 포커스 시 teal 외곽선 표시.

**빈 상태 CTA**
- [ ] 매물 탭 0건 시 "+ 매물 등록", 게시판 0건 시 "+ 글쓰기"(비로그인 시 로그인 유도), 시세 검색 무결과 시 "검색 지우기" CTA 노출.

**스크린리더 라벨(v1.94)**
- [ ] 시트/오버레이 닫기(×), 검색어 지우기(×), 사진 삭제(×) 버튼이 스크린리더에서 "닫기/검색어 지우기/사진 삭제"로 읽힘 + 키보드(Tab→Enter)로 동작.
- [ ] 매물·중개사 등록 폼 입력에 포커스 시 라벨("보증금(만원)" 등)이 읽힘(LField가 label로 연결됨). 통근/대출 슬라이더는 "통근 시간(분)/금리(%)/대출 기간(년)"으로 읽힘.

**앱 셸 캐싱 / 업데이트 배너(v1.93)**
- [ ] 빌드·서빙 후 접속 → DevTools>Application>Cache Storage에 `cj-shell-vN` 생성, `/assets/*`·`/icons/*` 캐시됨. **API 응답은 캐시에 없어야 정상**(시세 신선도).
- [ ] 2회차 방문 시 자산이 캐시에서 즉시 로드(Network에 (ServiceWorker) 표시).
- [ ] sw.js의 VERSION을 올려 재배포 → 재방문 시 "새 버전이 준비됐어요 · 새로고침" 배너 노출 → 새로고침 시 최신 반영. (첫 설치 때는 배너 안 뜸)

**오프라인 폴백(PWA, SPA 빌드 한정)**
- [ ] `npm run build` 후 `WEB_DIR=dist`로 서빙 → 브라우저에서 1회 접속(서비스워커 등록).
- [ ] DevTools > Network > Offline 체크 후 새로고침 → 브라우저 기본 오류 대신 **"인터넷에 연결되어 있지 않아요"** 안내 페이지가 뜸. "다시 시도" 클릭 시 reload.
- [ ] 온라인 복귀 후 정상 동작(자산·API는 SW가 가로채지 않으므로 평소와 동일, 업데이트 정상 반영).
- 참고: 오프라인 폴백은 frontend(dist) 기준. 레거시 app/web은 동결(미적용).

## K. 문의/리드 (B2B 첫 매출 기반) — v1.96
**문의 생성(사용자)**
- [ ] 매물 상세 하단 "온라인 문의 남기기" → 연락처·내용 입력 + 동의 체크 → "문의 보내기" → "문의를 보냈어요 ✓".
- [ ] 동의 미체크 시 전송 거부(400, "동의해야…"). 연락처/내용 빈 값 시 전송 거부.
- [ ] 숨김/없는 매물에 문의 시 404.

**리드 열람(중개사·소유자)**
- [ ] 중개사 대시보드 "받은 문의(리드)" 섹션에 문의 노출(이름·연락처·내용·날짜·매물명), "받은 문의" Stat, 매물 행에 "문의 N".
- [ ] 상태 버튼(읽음/연락함/종료) 동작 → 갱신. 신규는 "신규" 뱃지.
- [ ] **소유자만 열람**: 다른 계정/기기로 `/inquiries` 호출 시 본인 매물 문의만 반환(타인 문의 연락처 비노출). 상태 변경은 소유자만(403).

**개인정보(필수 후속)**
- [ ] 연락처 수집 → **개인정보처리방침에 '매물 문의 연락처' 항목 추가**(legal/privacy.md + PRIVACY_VERSION 상향 시 동의 재수집). 스토어 Data safety/App Privacy 라벨에도 반영.

## L. 결제/구독(첫 매출) — v1.97 · 기본 OFF
**기본(feature_billing=false) — 현재와 동일해야**
- [ ] `/config` feature_flags.billing=false. `/billing/plans`→enabled:false, `/billing/checkout`→404. 리드 연락처 **전체 노출**(마스킹 없음). 대시보드에 업그레이드 버튼 안 보임.

**활성(FEATURE_BILLING=true 후 재기동, BILLING_PROVIDER=mock)**
- [ ] 비프리미엄 중개사: `/inquiries` 응답 `locked:true`, contact=null. 대시보드 리드에 "🔒 Pro에서 연락처 확인" + "Pro 업그레이드" 버튼.
- [ ] "Pro 업그레이드" 클릭 → mock checkout→confirm → 구독 active → 리드 연락처 노출(locked 해제). `/billing/me` premium:true.
- [ ] `/billing/cancel` → status canceled, plan free. 다시 마스킹.
- [ ] toss/portone로 설정 시 checkout가 "키 필요" 메시지(스텁) — 실 PG는 키·웹훅 검증 구현 필요.
- 주의: 결제·구독 추가로 마이그레이션 필요 → `python -m scripts.db_upgrade`(head=0015).

## M. 검색 인덱스(pg_trgm) — v1.99 · PostgreSQL
- [ ] (PostgreSQL) `python -m scripts.db_upgrade`(head=0016) 후 인덱스 생성 확인:
      `\di+ ix_*_trgm` (psql) 또는 `SELECT indexname FROM pg_indexes WHERE indexname LIKE '%trgm%';`
- [ ] 인덱스 사용 확인(EXPLAIN): `EXPLAIN ANALYZE SELECT * FROM transactions WHERE complex_name LIKE '%복대%' AND deal_type='trade' LIMIT 500;` → Bitmap Index Scan on ix_tx_complex_trgm 가 보이면 OK(데이터가 충분할 때).
- [ ] `/search?q=...` 결과는 인덱스 적용 전후 **동일**해야 함(가속만, 결과 불변).
- [ ] (SQLite) 마이그레이션이 스킵되고 검색이 정상 동작(스캔 폴백).
- [ ] (관리형 DB) `CREATE EXTENSION pg_trgm` 권한 없으면 0016 실패 → DBA가 확장 활성화 후 재시도. (DEPLOY.md 참조)

## N. 지도 주기능 1단계 — v1.100 · 네이버 키 필요
- [ ] 하단 네비 6번째 "지도" 탭 노출, 탭 진입 시 지도 렌더(서버 .env NAVER_MAP_CLIENT_ID 필요, 도메인 등록).
- [ ] `/map/markers?deal_type=trade&property_type=apartment` → markers[]·bands·disclaimer 반환. 좌표 있는 단지만.
- [ ] 거래유형(매매/전세/월세)·주택유형(아파트/오피스텔/빌라) 칩 전환 시 마커·라벨 갱신(매매=평단가, 전세/월세=보증금 억 표기).
- [ ] 마커 색이 가격대(분위)별로 다름. 마커 클릭 → 해당 단지 상세 오픈.
- [ ] 좌표 미확인 단지는 지도에서 제외(왜곡 방지). 키 없으면 안내 문구. 인증 실패 시 안내.
- 주의: 지도 렌더는 샌드박스 검증 불가 — 실제 키·좌표(scripts.geocode)로 머신에서 확인.

## O. 지도 2단계 — 뷰포트 요약·클러스터링 — v1.101
- [ ] 지도 줌아웃 시 마커가 **묶음(예: "12곳")**으로, 줌인 시 개별 단지 가격 마커로 전환.
- [ ] 묶음 마커 클릭 → 해당 위치로 줌인. 개별 마커 클릭 → 단지 상세.
- [ ] 지도 이동/줌(idle) 후 상단 "이 지역" 패널의 곳 수·중앙값이 **보이는 영역 기준**으로 갱신(약 0.35s 디바운스).
- [ ] 거래유형/주택유형 전환 시 지도가 전체 마커에 맞게 재정렬(fit)되고 패널·색이 갱신.
- [ ] `/map/markers` 응답에 summary(count/median/avg) 포함. 패널 초기값은 전체 summary, 이동하면 뷰포트 기준.
- 주의: 지도 상호작용은 샌드박스 검증 불가 — NAVER 키+좌표로 머신에서 확인.

## P. 지도 3단계 — 영역 단지 목록·다중선택 비교 — v1.102
- [ ] 지도 패널의 "목록" 버튼 → 보이는 영역의 단지 시트(가격순/이름순 정렬). 각 행: 단지명·구/동·건수·대표가.
- [ ] 행 탭 → 단지 상세(시트 닫힘). ⊕ 버튼 → 비교함에 담김(✓로 표시, 최대 4개 초과 시 안내).
- [ ] 비교함에 담기면 하단 "비교하기" 트레이 노출 → 누르면 단지 비교(`/compare`) 오버레이.
- [ ] 지도를 이동/확대해 영역을 바꾸고 "목록"을 다시 열면 그 영역 단지로 갱신.
- [ ] 빈 영역에서 목록 → "표시할 단지가 없습니다" 안내.
- 주의: 구·동 경계 폴리곤·freehand 그리기는 미구현(GeoJSON·drawing SDK 필요). 지도 상호작용은 NAVER 키+좌표로 머신 확인.

## Q. 자동 테스트 — 문의·결제 (v1.104)
- `tests/test_inquiry.py`(8): 동의 필수(400)·소유자만 연락처 열람·숨김/없는 매물 404·타인 열람 0건·상태변경 소유자만(403/200)·summary 집계·식별 없으면 401.
- `tests/test_billing.py`(7): feature_billing OFF 기본 불변식(plans disabled·me disabled·checkout/confirm/cancel 404)·플랜 구조·mock checkout 토큰 발급.
- 레이트리밋: `POST /inquiries`·`/billing/*` 버킷 추가(conftest는 RATE_LIMIT_ENABLED=false라 테스트 무영향).
- ⚠️ 본 샌드박스엔 pytest/sqlalchemy 미설치 → **작성·문법검증만**. 통과는 머신에서 `pytest -q` 로 확인.

## R. 회원 탈퇴(계정 삭제) — v1.106
- `tests/test_account_delete.py`(4): 미인증 401·confirm 없으면 400·cascade 삭제+게시글 익명화·탈퇴 후 토큰 무효(/me 401).
- 수동: 계정 메뉴 > ‘회원 탈퇴’ → 확인 다이얼로그 → 삭제 후 로그아웃·새로고침. 내 관심/매물/문의 사라지고, 내가 쓴 글은 ‘탈퇴한 사용자’로 표시되는지.
- 보존 확인: 구독/결제·동의 이력은 남는지(법정 보존). ⚠️ 실 PG 도입 시 결제기록 보존정책 재점검.
