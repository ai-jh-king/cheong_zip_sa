# 🤝 Claude Code 인수인계서 (v1.176 → 다음)

> **이 문서는 웹 Claude에서 Claude Code로 옮겨오면서 작성된 최상단 인수인계서입니다.**
> 새 Claude는 이 문서를 **가장 먼저** 읽고, 그다음 `CLAUDE.md`를 읽어야 합니다.
> 마지막 작업 세션: 2026-06-28 · 현재 버전: **v1.176**

---

## 0. 사용자의 절대 원칙 (매 응답에서 지키기)

사용자가 세션마다 반복해서 강조한 것들:

1. **왜곡 없음 (distortion-free)** — 데이터·URL·API 응답을 지어내지 않는다. 검증 안 된 것은 config로 빼고 미설정 시 스킵. 판정("이 집 사세요/사지 마세요")이 아니라 **위치·차이·사실 + 면책**. 샘플 데이터는 반드시 `is_sample=True`로 격리.
2. **인수인계 가능 문서 (항상 갱신)** — 구조·진행사항·데이터·운영지침을 언제든 인수인계 가능 수준으로 유지. 새 기능/수정 시 관련 문서(`CLAUDE.md`·`ROADMAP.md`·`skills/*.md`·`CHANGELOG.md`)를 함께 갱신.
3. **Step by step, 꼼꼼히** — 큰 변경일수록 단계로 쪼갠다. 각 단계 검증 후 다음.
4. **대규모 서비스 대비** — "많은 사용자에게 서비스한다"고 가정. 확장성·성능·보안·데이터 영속성 고려.
5. **사용자를 먼저 파악하고 제안** — 대안·질문을 먼저 제시. 온보딩(청주가 처음이세요?)이 이 철학의 구현체.
6. **최신 UI 트렌드로 편하게** — 전체화면·큰 탭 타겟·한 화면 한 질문·미니멀. Tailwind 없이 인라인 스타일(main.jsx 단일 파일 관례).
7. **실제 앱처럼 테스트** — 정적 검증만 믿지 말고 실행으로 확인.
8. **서비스 단계 = 실수 금지** — v1.163·v1.166·v1.174 등 정적 검사 통과했지만 런타임 크래시된 사고들이 있었음. 사용자는 "이런 실수 다시는 하지마라"고 명시. 반드시 3층 검증(§5).

---

## 1. 프로젝트 정체성 (전략)

**청집사 (cheong-zipsa)** — 청주시 부동산 정보 통합 플랫폼.

### 3층 해자
1. **해자 (이해상충 없음)**: 중개·광고 수익 0 → "말릴 수 있는 앱". 대형 앱(네이버·호갱노노·직방)이 구조적으로 못 하는 "이 집 비쌉니다"·"역전세 위험"·"급매 포착"을 정면에 배치.
2. **창끝 (전입자 온보딩)**: SK하이닉스·오송·오창 발령자 등 청주가 낯선 신규 수요층 타깃. "청주가 처음이세요?" 3단계 위저드.
3. **복리 (주민 인증 커뮤니티)**: 서버가 우리집 등록과 대조해 위조 불가능한 주민 뱃지. 데이터 축적 → 후발주자 추격 불가.

### 메인 기능 = "판단이 얹힌 지도" (v1.169 결정)
유입·체류는 지도가 만들고(부동산 앱 사용자의 첫 본능), 차별화는 지도 위 우리만의 시그널(📉급매·🏗호재·현위치)이 만든다. "가격만 찍힌 지도"가 아니라 판단 재료가 얹힌 지도가 우리의 정체성.

---

## 2. 현재 상태 스냅샷 (v1.176)

### 완비 (작동, 데이터 있음)
- 실거래 시세·추이(1·3·5년 토글)·랭킹
- 지도(마커·전체화면·📉급매·🏗호재 핀 토글·📍현위치)
- 단지 상세(면적 병합·거래활발·**전세가율 신호**·직주근접·인프라·**호가검증**·단지이야기)
- 우리집(시세변동·서버동기화)
- 관심단지 시세, 청약, 대출/세금 계산기
- 게시판(**주민 뱃지** — 우리집 서버 대조)
- **전입자 온보딩 위저드** (직장→예산→가족→맞춤 결과)
- **급매 레이더** (홈 카드·지도 핀)
- 더보기: **🛡 전세 안전 진단**(깡통전세 계산기+체크리스트), **🔎 계약 전 확인 공식 링크 10종**
- 유입 장치: 공유 카드 워터마크·호가검증 공유·친구 알리기·SEO 랜딩(/r·/c·sitemap)

### 구조만 완성 (데이터 대기)
- 🧸 육아·초품아·지도 POI → 시설 데이터 적재 대기 (NEIS 학원 키 + data.go.kr URL 설정 필요, DATA_PLACES.md 참조)

### 검증 체계 (3층 — 매 변경 후 반드시)
1. **정적**: `python -m scripts.verify_all` (compileall + import/속성 심볼 + 프런트 무결성 + 훅 정합 + 함수 중복)
2. **단위/회귀**: `pytest` — **147개 (v1.176 기준 148)** 통과
3. **통합(실제 앱)**: `python -m scripts.smoke_e2e` — TestClient로 17여정 검증 (v1.176 기준 18)

### 알려진 부채
1. **운영이 SQLite면 재배포 시 데이터 소실** → **PostgreSQL 전환이 최우선** (지금 미완, 다음 작업)
2. **`frontend/src/main.jsx` 4,800+줄 단일 파일** — 사용자 늘기 전 분리 권장 (지금은 리스크 대비 이득 낮음)
3. **프런트 GU_NAME/GU_NAMES 중복 정의** — 충청도 확장 시 통합 필요

---

## 3. ⚠️ 진행 중이던 작업 (다음 즉시 할 일)

### 🔥 미완: 카카오 로그인 KOE101 해결
- **네이버 로그인은 성공** (v1.176 수정 후)
- **카카오만 KOE101 = "앱 관리자 설정 오류"** 상태
- 사용자가 카카오 개발자센터에서 확인 중이었음
- 확인 순서 (SOCIAL_LOGIN_DEBUG.md §7 참조):
  1. **REST API 키 일치 확인** — 브라우저 URL의 `client_id=d831efcb9e13f2ce6e876ae77b39a8ce`가 콘솔의 REST API 키와 같은지
  2. **Web 플랫폼 사이트 도메인 등록** (앱 설정 → 플랫폼 → Web) — `http://localhost:8000` 추가
  3. **카카오 로그인 활성화 ON**
- 코드는 이미 v1.176에서 완비됨:
  - redirect_uri URL 인코딩
  - Client Secret 지원 (`KAKAO_LOGIN_CLIENT_SECRET` env 선택)
  - 콜백 실패 사유를 URL(`?login=error&provider=kakao&why=...`)·로그에 노출

**사용자 마지막 메시지**: "카카오로 시도해뷸게" (자리 잠깐 비운 상태)

### 다음 큰 작업: **PostgreSQL 전환 → 실배포**
로그인 해결 후 이어질 순서 (OPERATIONS.md §7 참조):
1. Render 대시보드 → New + → PostgreSQL 생성 (같은 리전)
2. Internal Database URL을 웹 서비스 env `DATABASE_URL`에 설정 → 재배포
3. Shell에서: `python -m scripts.preflight` → `python -m scripts.db_upgrade` (head 0019) → `python -m scripts.doctor`
4. `python -m scripts.seed_landmarks`·`seed_commute`·`run_collect live`
5. 자동 수집 Cron Job 생성 (`python -m scripts.scheduler --once`, `0 19 * * *`)
6. 브라우저 스모크

---

## 4. Claude Code 환경에서 처음 할 일

```bash
# 1) 프로젝트 진입
cd <프로젝트 경로>          # 예: C:\Claude_Pjt\cheong_zip_sa\cheongju-realestate

# 2) 의존성 (한 번만)
pip install -r requirements.txt --break-system-packages
cd frontend && npm install && cd ..

# 3) 검증 3층 (지금 상태 확인)
python -m scripts.verify_all
JWT_SECRET="x_test_secret_key_at_least_32_characters_long" AUTH_DEV_LOGIN=true pytest
JWT_SECRET="x_test_secret_key_at_least_32_characters_long" AUTH_DEV_LOGIN=true python -m scripts.smoke_e2e

# 4) 로컬 실행 (백엔드+프런트)
cd frontend && npm run build && cd ..    # 프런트 빌드
python run.py                             # http://127.0.0.1:8000

# 또는 개발 편의 (Vite dev):
python run.py                             # 백엔드 :8000
cd frontend && npm run dev                # 프런트 :5173 (별 창)
```

### `.env` 필수 (로컬)
```
JWT_SECRET=local_dev_secret_at_least_32_chars_ok
AUTH_DEV_LOGIN=true                       # 로컬 개발용 (운영은 반드시 false)
AUTH_REDIRECT_BASE=http://localhost:8000  # 소셜 로그인 콜백 base

# 소셜 로그인 (미설정 시 소셜 버튼 미노출, dev-login으로 대체)
KAKAO_LOGIN_REST_KEY=<카카오 REST 키>
KAKAO_LOGIN_CLIENT_SECRET=<카카오 Client Secret 사용 ON한 경우만>
NAVER_LOGIN_CLIENT_ID=<네이버 Client ID>
NAVER_LOGIN_CLIENT_SECRET=<네이버 Client Secret>

# 실거래 (없으면 샘플 fixtures 사용, 실데이터 없음)
MOLIT_SERVICE_KEY=<data.go.kr 실거래가 키>

# 지도 (없으면 지도 안 뜸)
NAVER_MAP_CLIENT_ID=<네이버 클라우드 지도 Client ID>
KAKAO_JS_MAP_KEY=<카카오 JavaScript 키>       # 지도 옵션
```

---

## 5. 매 변경 후 필수 루틴 (사용자 원칙 이행)

```bash
# ① 정적 게이트 (모든 커밋 전 필수, compileall이 못 잡는 사고 차단)
python -m scripts.verify_all

# ② 회귀 테스트
JWT_SECRET="x_test_secret_key_at_least_32_characters_long" AUTH_DEV_LOGIN=true pytest

# ③ 통합 스모크 (실제 HTTP 여정)
JWT_SECRET="x_test_secret_key_at_least_32_characters_long" AUTH_DEV_LOGIN=true python -m scripts.smoke_e2e

# ④ 세 개 다 PASS 시에만: 문서 갱신 + VERSION 업 + CHANGELOG 엔트리
```

**정적 게이트만으로는 부족했던 실제 사고들 (교훈, CLAUDE.md에도 기록):**
| 버전 | 사고 | 오프라인 검사가 통과한 이유 |
|---|---|---|
| v1.156→163 | `complex_detail` 정의 유실 (def 줄이 흡수됨) | 문법 정상 → compileall 통과, 하지만 런타임 ImportError |
| v1.156→166 | `@stat_cached` 데코레이터 전이 → 전세가율 왜곡 | 함수는 존재, 하지만 캐시가 첫 인자만 봄 → 모든 단지 같은 값 |
| v1.158→165 | posts.resident 컬럼 누락 (SQLite `_ensure_columns` 수동 목록 드리프트) | 마이그레이션은 있으나 SQLite 자가보강 리스트 갱신 안 됨 |
| v1.169→174 | 지도 탭 진입 즉시 크래시 (`useRef` 구조분해 누락) | JS 구문 정상 → 정적 검사 통과, 런타임 ReferenceError |
| v1.170→173 | JeonseSafety 중복 정의 (앞 정의 덮어씀) | 두 함수 다 유효 문법 |

**이런 사고를 이제 `verify_all`이 자동으로 잡습니다:**
- import/속성 심볼 정합 (complex_detail 유형)
- React 훅 정합 (useRef 유형)
- 최상위 함수 중복 정의 (JeonseSafety 유형)
- SQLite 컬럼 자가보강은 이제 Base.metadata 자동 도출 (수동 목록 드리프트 불가)

**데코레이터 전이는 아직 정적 검사 없음** → def 줄 str_replace 시 주의(CLAUDE.md 함정 기록).

---

## 6. 코드 구조 요약 (익숙해지려면)

```
cheongju-realestate/
├── app/                          # FastAPI 백엔드 (~10,100줄)
│   ├── main.py                   # 엔트리, 라우터 등록
│   ├── api/                      # 라우터 (auth·complex·pricecheck·community·onboarding·...)
│   ├── services/                 # 비즈니스 로직 (stats·pricecheck·onboarding·commute·...)
│   ├── sources/                  # 외부 API 커넥터 (molit·applyhome·neis·daycare·...)
│   ├── models/__init__.py        # SQLAlchemy 모델 전체
│   ├── data/region_codes.py      # ★ 지역코드 단일 소스 (충청 확장 시 이것 + 4곳)
│   ├── db/session.py             # DB 초기화 + _ensure_columns (모델 자동 도출)
│   └── core/config.py            # 모든 env·설정
├── frontend/
│   ├── src/main.jsx              # ★ 프런트 단일 파일 (4,800+줄)
│   ├── capacitor.config.json     # 앱 스토어 배포용 (v1.168~)
│   └── package.json              # Vite + Capacitor
├── migrations/versions/          # Alembic (head = 0019_post_resident)
├── scripts/                      # 운영 스크립트
│   ├── verify_all.py             # ★ 정적 게이트 (매 변경 후)
│   ├── verify_imports.py         # import/속성 심볼
│   ├── verify_frontend.py        # 프런트 무결성 + 훅 정합 + 중복 함수
│   ├── smoke_e2e.py              # ★ 실제 앱 e2e (v1.166 신설)
│   ├── preflight.py              # 배포 자가진단
│   ├── doctor.py                 # DB·데이터 건수 확인
│   ├── db_upgrade.py             # Alembic 래퍼
│   ├── run_collect.py            # 실거래 수집
│   ├── scheduler.py              # 자동 수집 (--once 지원)
│   ├── seed_landmarks.py         # 호재 시드
│   ├── seed_commute.py           # 통근거점 시드
│   ├── geocode.py                # 지오코딩 (places 포함)
│   └── collect_places.py         # 시설 수집
└── tests/                        # pytest (147개 → v1.176 148개)
```

### 문서 위계 (읽는 순서)
1. **HANDOFF_TO_CLAUDE_CODE.md** ← 이 문서
2. **CLAUDE.md** — 프로젝트 개관, 8.0 전략, 8.1 최근 기능, 함정 목록
3. **ROADMAP.md** — 현재상태 스냅샷, 우선순위, 릴리스 규율
4. **TESTING.md** — 검증 3층
5. **OPERATIONS.md** — 배포·장애 대응 (§7 SQLite 함정!)
6. **AUDIT.md** — 전면 감사 결과 (v1.167)
7. **SOCIAL_LOGIN_DEBUG.md** — 카카오·네이버 진단
8. **CHANGELOG.md** — 전 버전 이력

### 도메인 문서
- **DATA.md** — 실거래·모델 규칙
- **DATA_PLACES.md** — 시설 데이터 (학원·어린이집·의료·도서관·체육)
- **LANDMARKS.md** — 호재 시드
- **MOBILE_APP_STRATEGY.md**·**MOBILE_DEPLOY.md** — 앱 배포 (Capacitor)
- **LAUNCH.md** — 출시 체크리스트
- **DEPLOY.md**·**CUTOVER.md** — 배포 세부
- **MONETIZATION.md** — 지금 OFF, 구조만 준비 (부록 B 원칙)
- **QUICKSTART.md** — 빠른 시작

---

## 7. 릴리스 규율 (사용자 관례)

- 매 변경 후: 3층 검증 (§5)
- 문서 함께 갱신: `CLAUDE.md` (기능·함정) · `ROADMAP.md` (스냅샷) · 관련 `skills/*.md` · `CHANGELOG.md` (신규 엔트리)
- `VERSION` 파일 업데이트 (현재 1.176 → 다음 1.177)
- 패키징: zip 최상위 폴더명 반드시 `cheong_zip_sa` (사용자님 다운로드 관례)
  ```bash
  cd .. && rm -rf /tmp/pkg && mkdir -p /tmp/pkg
  cp -a cheongju-realestate /tmp/pkg/cheong_zip_sa
  find /tmp/pkg/cheong_zip_sa -type d \( -name __pycache__ -o -name node_modules -o -name .pytest_cache \) -prune -exec rm -rf {} + 2>/dev/null
  find /tmp/pkg/cheong_zip_sa -name "*.db" -delete
  cd /tmp/pkg
  zip -q -r cheong_zip_sa_v1_<VERSION>.zip cheong_zip_sa -x "*.DS_Store"
  zip -q -r -P 'cheongju2026' cheong_zip_sa_v1_<VERSION>_secured.zip cheong_zip_sa -x "*.DS_Store"
  ```

---

## 8. 커뮤니케이션 스타일 (사용자와의 관계)

- **한국어**로 답한다.
- 사용자는 종종 짧게 씀 ("진행해", "확인해", "ㄱㄱ"). 컨텍스트를 정확히 파악하는 게 중요.
- **오타 자주 있음** — 의미 파악해서 진행.
- 사용자는 **판단·근거·솔직함**을 원함. "됐나?"에 "네"가 아니라 근거 있는 판정을 요구.
- 실수 지적 시 **변명하지 않고** 원인·조치·재발방지를 보여줌.
- 사용자가 원하지 않는 것: 코드만 파는 것. **전략·서비스 관점**도 함께 봐야 함.

### 사용자가 이번 세션에서 한 대표적 지적들
- "너무 코드적으로만 생각한다" → 서비스 전략·사람의 습성을 파악하고 창조하라
- "청주 타겟의 서비스처럼" → 하이퍼로컬 특화
- "서비스 할 단계급인데. 이런 실수 다시는하지마라" → 서비스 단계에 걸맞는 품질
- "실제 앱처럼 테스트해야해" → 정적 검사만으론 부족, 실행 검증 필수
- "판단이 잘 짜졌는지" → 전략도 감사 대상
- "링크만 말고 상세하게" → 단순 연결 아닌 앱 내 계산·상세 제공

---

## 9. 지금 이 시점에서 새 Claude가 처음 할 것

1. **이 문서 정독** + `CLAUDE.md` 정독
2. `python -m scripts.verify_all` 실행 → PASS 확인
3. `pytest` 실행 → 148 passed 확인
4. `python -m scripts.smoke_e2e` 실행 → 18 PASS 확인
5. 사용자에게 "v1.176 상태 확인 완료, 카카오 KOE101 이어서 진행하시겠어요, 아니면 PostgreSQL 전환부터?"

---

## 10. 마지막으로 — 이 프로젝트의 정신

> "청집사는 아무것도 팔지 않습니다. 그래서 말릴 수 있습니다."

중개도, 광고도, 이해상충 없이 청주 실수요자 편에만 서는 앱입니다. 모든 신호는 **참고·근거·면책**이고, 가격도 사람도 지어내지 않습니다. 이 정체성이 대형 앱이 못 하는 우리만의 해자예요. 새 기능을 만들 때마다 "이게 사용자 편이 맞는가?"를 물어보세요.

—
**작성일: 2026-06-28 · 세션 종료 시점 버전: v1.176 · 다음 세션 예상 버전: v1.177**
