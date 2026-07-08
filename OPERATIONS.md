# 운영 가이드 (OPERATIONS) — 청주 부동산 플랫폼

> 운영자가 이 문서만 보고 **설치 → 실행 → 일상 운영 → 배포 → 모니터링 → 장애대응**을 할 수 있도록 정리했습니다.
> 개발/구조 세부는 `README.md`·`CLAUDE.md`·`ROADMAP.md`·`skills/`를 참고하세요.

---


## 배포 자가진단 (가장 먼저 실행)
> 코드 반영 전 로컬/CI에서 **`python -m scripts.verify_all`** (정적 게이트, PASS 필수) → 그다음 아래 preflight(env·시크릿).

설정·DB·마이그레이션·지역코드 실조회·데이터 신선도·연동 키·백업 준비를 한 번에 점검합니다.

```
python -m scripts.doctor            # 전체(실데이터 1회 조회 포함)
python -m scripts.doctor --skip-live   # 외부 API 호출 생략
```

각 항목이 ✅/⚠️/❌ 로 표시되고, ❌ 가 없으면 배포 준비 완료입니다. 푸시·모니터링·백업 등 그동안 추가한 백엔드가 실제로 동작하는지 이 한 번으로 확인하세요.

## 0. 한눈에 (TL;DR)
```bash
# 1) 키 준비: .env 작성 (아래 1장)
cp .env.example .env      # 값 채우기 (윈도우: copy)

# 2) 최초 실행 (의존성 자동설치 + DB생성 + 수집 + 서버)
python run.py             # http://localhost:8000

# 3) 데이터 다시 쌓기(더미가 선점했거나 키 새로 넣었을 때)
python run.py --refresh
```
- **MOLIT_SERVICE_KEY(data.go.kr 디코딩 키)가 없으면 실데이터 대신 모의데이터(is_sample)** 가 쌓입니다(화면에 '모의데이터 포함' 배너).
- 운영 배포 전 반드시: `JWT_SECRET`·`ADMIN_TOKEN` 설정, `AUTH_DEV_LOGIN=false`, DB를 PostgreSQL로.

---

## 1. 사전 준비 — 키 발급과 .env

모든 공공데이터는 **data.go.kr 계정 인증키 1개(`MOLIT_SERVICE_KEY`)** 로 공통 호출합니다. 데이터셋별로 **'활용신청'만 추가**하면 됩니다.

| 환경변수 | 용도 | 발급처/주의 |
|---|---|---|
| `MOLIT_SERVICE_KEY` | 실거래 8종·청약·정책대출·서민금융 | data.go.kr → 활용신청 → **디코딩(Decoding) 키**. 승인 1~24시간 |
| `KAKAO_REST_API_KEY` | 지오코딩(좌표)·인근 POI·학군 | 카카오 개발자 콘솔 → 앱 → **카카오맵(로컬) 사용 설정 ON** |
| `NAVER_MAP_CLIENT_ID/SECRET` | 지도 표시(JS SDK) | 네이버클라우드 Maps. (지오코딩은 기본 카카오) |
| `FINLIFE_API_KEY` | 대출 금리 비교공시 | 금감원 '금융상품 한눈에'(별도 신청) |
| `KAPT_LIST_URL`,`KAPT_INFO_URL` | 단지 기본정보(세대수 등) | data.go.kr 공동주택 단지목록·기본정보 활용신청 후 **Swagger로 요청주소 확인**해 입력 |
| `JWT_SECRET` | 로그인 세션 서명 | **배포 필수**. `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `ADMIN_TOKEN` | 관리자 API 활성화 | 길고 무작위. 미설정이면 `/admin/*` 비활성 |

> `.env`는 절대 git에 커밋하지 마세요(.gitignore 포함). 키가 노출되면 즉시 재발급하세요.

**활용신청이 필요한 data.go.kr 데이터셋(실거래)**: 아파트/오피스텔/연립다세대/단독다가구 각 매매·전월세(8종), 분양권 전매.

---

## 2. 최초 실행 (로컬/단일 서버)

```bash
python run.py
```
`run.py`가 자동으로: 의존성 설치 → DB 테이블 생성 → 예시/실데이터 수집 → 서버 기동(:8000).

- **이미 데이터가 있으면 수집을 건너뜁니다.** 다시 쌓으려면 `python run.py --refresh`.
- 키가 정상인데 더미만 나오면 3장(장애대응) 참고.

수동 단계 실행이 필요하면:
```bash
python -m scripts.run_collect          # 실거래 수집(증분)
python -m scripts.geocode              # 단지 좌표(지오코딩)
python -m scripts.enrich               # 단지 기본정보(K-apt) 보강
python -m scripts.import_gongsi --path 공동주택가격.csv   # 공시가격 보강(아래 4장)
python -m scripts.verify_region_codes  # 지역코드/키 점검(401 진단)
```

---

## 3. 일상 운영

### 3.1 데이터 자동 갱신 (스케줄러 / Render 크론)
```bash
python -m scripts.scheduler            # 상시 루프: 주기적으로 수집 + 지오코딩(단지·시설)
python -m scripts.scheduler --once     # 1사이클만 실행 후 종료(크론용)
```
- 주기: `.env`의 `SCHEDULER_INTERVAL_HOURS`(기본 24). 실수집: `SCHEDULER_RUN_COLLECT=true`(MOLIT 키 있을 때만).
- 지오코딩은 **단지 + 시설(Place)** 모두 수행(키 없으면 자동 스킵). 수집 시 관심 단지 신규 실거래 알림·정정/해제 반영 자동.

**Render에서 자동화 켜기 (둘 중 하나):**
- **A. 대시보드에서 Cron Job 생성(기존 수동 배포 사용자 — 권장)**: Render 대시보드 → New + → **Cron Job** → 이 저장소 선택(runtime Docker) → Schedule `0 19 * * *`(한국 04:00) → Command `python -m scripts.scheduler --once` → Environment에 `DATABASE_URL`(웹 서비스와 같은 DB의 Internal URL), `MOLIT_SERVICE_KEY`, (선택)`KAKAO_REST_API_KEY` 입력 → 생성. 첫 실행은 "Trigger Run"으로 즉시 테스트.
- **B. Blueprint(render.yaml)**: 저장소의 render.yaml에 cron이 활성화돼 있음 → Blueprint Apply 시 웹+DB+크론이 함께 생성. ⚠️ **이미 수동으로 서비스를 만든 경우 Apply 금지**(중복 생성) — A 방식 사용.
- 확인: 실행 후 `/health`의 `last_collect_at` 갱신, 관리자 API `X-Admin-Token`으로 JobRun 이력 조회.
- (로컬/자체 서버라면) 이 프로세스를 systemd/pm2로 상시 실행하거나 OS 크론으로 `--once` 호출.

### 3.2 관리자 API (헤더 `X-Admin-Token: <ADMIN_TOKEN>`)
| 메서드/경로 | 기능 |
|---|---|
| `GET /admin/status` | 작업 상태 + 지오코딩 커버리지 |
| `POST /admin/collect?months=0&geocode=true` | 수집 실행(백그라운드) |
| `POST /admin/geocode?limit=0` | 좌표 보강 |
| `POST /admin/enrich?limit=0` | 단지 기본정보(K-apt) 보강 |
| `GET /admin/ui` | 토큰 입력형 간단 관리 화면 |

### 3.3 단지 데이터 보강
- **세대수·동수·사용승인일·난방·연면적·시공사·주차(K-apt)**: `KAPT_LIST_URL/KAPT_INFO_URL` 설정 후 `python -m scripts.enrich` 또는 `POST /admin/enrich`. 미설정·미매칭은 보강하지 않음(null).

---

## 4. 공시가격 보강 (공식 CSV)

공동주택 공시가격은 깔끔한 단지단위 API가 없어 **공식 CSV**로 보강합니다.
1. data.go.kr '공동주택 공시가격' 데이터(또는 부동산공시가격알리미 자료)를 받습니다. 대용량이면 **충북/청주로 필터**하세요.
2. 실행:
```bash
python -m scripts.import_gongsi --path /경로/공동주택가격.csv
```
- 청주 4개 구만, **단지×면적 호별 가격의 중앙값(원→만원)** 으로 집계해 단지에 저장합니다.
- 단지명 매칭 실패는 보강하지 않습니다(null 유지·날조 금지). CSV 헤더가 다르면 `app/services/gongsi.py`의 후보 컬럼을 확인·조정하세요.

---

> 배포 시 마이그레이션: `python -m scripts.db_upgrade` (현재 head **0019_post_resident**).

## 5. 운영 배포 (스테이징/프로덕션)

### 5.1 필수 환경값
- `APP_ENV=production`, `AUTH_DEV_LOGIN=false`
- `JWT_SECRET`(고정·무작위), `ADMIN_TOKEN`(무작위)
- `DATABASE_URL=postgresql+psycopg://user:pw@host:5432/cheongju` (운영은 PostgreSQL 권장)
- `RATE_LIMIT_ENABLED=true`(기본), 필요시 분당 한도 조정
- CORS: `app/main.py`의 `allow_origins=["*"]`를 **실제 도메인으로 제한**

### 5.2 DB 마이그레이션 (운영은 alembic)
- 로컬/개발은 자동 `create_all`로 충분합니다.
- **운영은 alembic으로 스키마 관리**:
```bash
python -m scripts.db_upgrade        # 현재 설정 DB에 alembic upgrade head
# 또는: alembic upgrade head
```
- 이미 테이블이 있는 기존 DB로 처음 도입 시: `alembic stamp head` 후 이후 변경부터 마이그레이션 적용.
- 마이그레이션 파일: `migrations/versions/`(0001~0006). 새 컬럼/테이블은 모두 추가형이라 안전합니다.

### 5.3 컨테이너
- `docker-compose.yml` 제공(백엔드 + PostgreSQL). 비밀은 환경변수로 주입.
- 다중 워커/인스턴스 시 주의: **레이트리밋·집계 캐시는 프로세스별**입니다. 전역 제한·공유 캐시가 필요하면 Redis로 확장(구조 동일).

### 5.4 테스트/CI
```bash
pip install -r requirements.txt && pytest      # 회귀 테스트
```
GitHub Actions(`.github/workflows/ci.yml`)가 push/PR마다 컴파일+pytest를 실행합니다. **배포 전 pytest 통과를 확인**하세요.

---

## 6. 모니터링 (매일 확인)

| 점검 | 방법 | 정상 |
|---|---|---|
| 서버/DB 생존 | `GET /health` | `status:"ok"`, `db_ok:true` |
| 데이터 신선도 | `GET /status/data` | `stale:false`, `data_as_of` 최신, `last_collect.new/corrected/canceled` |
| 구별 커버리지 | `GET /status/data` → `per_gu` | 4개 구 모두 `count>0`, `latest` 최근 |
| 지오코딩 | `GET /status/data` → `geocode.coverage_pct` | 충분히 높음 |

- 화면 상단에 **"데이터 기준 YYYY-MM-DD · N일 전 갱신"** 이 표시되며, 36시간 넘게 미갱신이면 **⚠ 갱신 지연** 으로 바뀝니다 → 스케줄러/수집을 점검하세요.
- 로그: httpx 외부호출 소음은 억제되어 있고, 요청은 `method path -> status ms` 형식으로 남습니다. 운영에선 `LOG_LEVEL=INFO`.

---

## 7. 장애 대응 (실제 사례)

### 🚨 'no such column' + 데이터 전체 안 보임 — 원인: 운영이 SQLite 로 돌고 있음
- **증상**: 게시판 `no such column: posts.resident`(SQLite 어투), 시세·목록 등 데이터가 비어 보임.
- **원인**: `DATABASE_URL` 미설정 → **SQLite 폴백**. SQLite 파일은 컨테이너 재배포 때 **초기화**(영속 디스크 없으면)되어 데이터가 사라지고, 과거 생성된 테이블에 신규 컬럼(resident)이 없어 쿼리 실패.
- **확정**: `python -m scripts.doctor` 또는 `/health` 에서 DB 종류·데이터 건수 확인. `DATABASE_URL` 이 비어 있으면 SQLite.
- **해결(운영 필수)**:
  1) Render 관리형 **PostgreSQL** 생성 → 웹 서비스 env `DATABASE_URL`(Internal URL) 설정 → 재배포.
  2) `python -m scripts.db_upgrade`(→head, 스키마 생성/최신화).
  3) 최초 수집 `python -m scripts.run_collect live` + 크론(3.1) 활성화.
- **참고**: SQLite 환경이라도 앱 시작 시 `_ensure_columns`(모델 자동 도출)가 신규 컬럼을 보강하므로 재시작만으로 'no such column' 은 해소됨. 단 **데이터 영속성은 PostgreSQL 이어야** 보장됨.



| 증상 | 원인 | 조치 |
|---|---|---|
| **시세가 더미(모의)만 나옴** | `.env` 미작성/`MOLIT_SERVICE_KEY` 없음, 또는 더미가 선점 | `cp .env.example .env`로 키 입력 → `python run.py --refresh` |
| **수집 0건 / 401** | 데이터셋 활용신청 누락, 인코딩 키 사용, 승인 지연 | `python -m scripts.verify_region_codes`로 진단, **디코딩 키** 확인 |
| **네이버 지오코딩 401** | 네이버 Maps가 신 게이트웨이(maps.apigw.ntruss.com)로 이전 | 기본값이 **카카오 지오코딩**(`GEOCODE_USE_NAVER=false`)이라 무시 가능. 네이버를 쓰려면 신 호스트로 |
| **카카오 403 (로컬 API)** | 앱에 카카오맵(로컬) 권한 OFF, 또는 정책 차단 | 카카오 콘솔에서 카카오맵 제품 사용설정 ON, 차단 메일 조치. 응답 `code:-3`이면 권한 문제 |
| **로그인이 자꾸 풀림(재시작 시)** | `JWT_SECRET` 미설정 → 프로세스마다 임시 키 | `.env`에 고정 `JWT_SECRET` 설정 |
| **요청이 429** | 레이트리밋 초과 | 정상 보호. 필요시 `RATE_LIMIT_*_PER_MIN` 상향 |
| **단지정보/공시가격 안 채워짐** | KAPT URL 미설정/미매칭, 공시 CSV 미제공 | 4·3.3장 참고. 미매칭은 의도적으로 null(날조 안 함) |

---

## 7.5 외부 API 주소(URL)가 바뀌었을 때
공급사 정책/도메인 이전으로 API 주소가 바뀌면 **코드 수정 없이 `.env`만** 고치면 됩니다(재시작 필요).
- 대상: `MOLIT_BASE_URL`, `NAVER_GEOCODE_URL`, `KAKAO_KEYWORD_URL`, `KAKAO_ADDRESS_URL`, `KAKAO_CATEGORY_URL`, `FINLIFE_BASE_URL`, `APPLYHOME_URL`, `NEWS_URL`, OAuth(`KAKAO_*_URL`/`NAVER_*_URL`), 단지보강(`KAPT_*_URL`), 청약(`APPLYHOME_COMPETITION_URL`), 정책대출(`HF_POLICY_API_URL`), 서민금융(`SEOMIN_API_URL`).
- 비워두면 코드 기본값을 사용합니다. 값을 넣으면 그 주소로 호출합니다.
- 예: 네이버 지오코딩이 또 이전되면 `NAVER_GEOCODE_URL`만 새 주소로 교체.

## 8. 법무·개인정보 (운영 책임)
- **개인정보처리방침·이용약관은 템플릿**입니다(`app/web/legal/`). 시행 전 **개인정보/법무 전문가 검토**와 `[운영자 입력]`(상호·연락처·보유기간 등) 확정이 필요합니다.
- 정책 문구를 바꾸면 `app/api/legal.py`의 `PRIVACY_VERSION`/`TERMS_VERSION`을 올리세요(동의 이력이 새 버전으로 재수집됨).
- 대출 민감정보(소득·신용)는 **서버에 저장하지 않습니다**(추정은 무상태). '저장' 선택 시 사용자 브라우저에만 보관됩니다. 이 원칙을 깨는 변경은 처리방침·동의 절차를 함께 갱신하세요.
- 공공데이터 **출처표기 의무**(예: "자료: 국토교통부 실거래가")를 유지하세요. 뉴스 원문 전재 금지.

---

## 9. 정기 점검 체크리스트
- **매일**: `/health`·`/status/data`로 생존·신선도 확인(stale 아닌지).
- **주간**: 구별 커버리지·지오코딩 커버리지 확인, 로그 에러 점검, 디스크/DB 용량.
- **월간**: 공시가격 CSV 갱신 시 재임포트, 정책(LTV/DSR·세금) 변동 시 설정값 갱신, 키 만료/쿼터 점검, 의존성 보안 업데이트.
- **분기/정책 변경 시**: 처리방침·약관 검토 및 버전 갱신, 백업·복구 점검.

---

## 10. 백업·보안 요약
- DB 정기 백업(PostgreSQL `pg_dump`). 업로드 이미지(`UPLOAD_DIR` 또는 S3) 백업.
- 비밀은 환경변수/시크릿 매니저로만. `.env`·키를 코드·채팅·이슈에 노출 금지.
- 운영 CORS 도메인 제한, `AUTH_DEV_LOGIN=false`, `ADMIN_TOKEN` 강력하게.
- 사고 시: 노출 키 즉시 재발급, 관련 토큰 로테이션(`JWT_SECRET` 교체 시 전체 로그아웃됨).

### 마이그레이션 오류: invalid interpolation syntax (% in URL)
- 원인: DATABASE_URL 비밀번호의 `@`→`%40` 등 `%` 가 ConfigParser 보간과 충돌(구버전).
- 해결: v1.8+ 적용(env.py 가 URL 을 직접 사용). 또는 비밀번호를 영숫자로 바꿔 인코딩 불필요하게.

### 마이그레이션 오류: boolean 컬럼에 integer (DatatypeMismatch)
- 증상: `열 is_canceled 은 boolean 인데 표현식은 integer` / `UPDATE ... = 0`.
- 원인: SQLite(bool=0/1)용 raw SQL 이 PG(엄격한 boolean)에서 실패. v1.9 에서 `= false` 로 수정.
- 해결: v1.9+ 적용 후 `db_upgrade current` 로 현재 리비전 확인 → `db_upgrade upgrade head` 재실행(0003부터 이어서 적용).
- 운영(PG)은 스키마를 Alembic 만으로 관리(run.py 는 PG 에서 create_all 하지 않음).

## 데이터 구조 설명서
운영자용 데이터 저장 구조·컬럼·흐름·집계 기간·PostgreSQL 확인 방법은 **[DATA.md](./DATA.md)** 참조.

## 청주 특화 데이터 적재 (호재·직주근접·시설)
> 왜곡 없음: 아래를 적재하기 전까지 해당 UI는 **렌더되지 않음**(빈 화면 아님). 적재 즉시 활성.

| 기능 | 적재 명령 | 필요 키 | 상태 |
|---|---|---|---|
| 🏗 개발 호재(홈 카드·지도 핀) | `python -m scripts.seed_landmarks` | 없음(시드 내장) | 데이터 준비됨 → 실행만 |
| 🏭 직주근접(직장·거점 거리) | `python -m scripts.seed_commute` | 없음(정밀좌표는 `--geocode`+카카오) | 데이터 준비됨 → 실행만 |
| 🧸 육아·초품아·지도 POI | `python -m scripts.collect_places all` → `python -m scripts.geocode places` | **NEIS(학원)** + data.go.kr(어린이집 등) | 키 발급 필요 |

- **호재 갱신**: `scripts/seed_landmarks.py`의 `LANDMARKS` 리스트를 편집(사실·출처 필수) 후 재실행. 멱등(name 기준 upsert). 좌표 없으면 지도 핀 제외(홈 카드엔 표시).
- **시설(NEIS 학원)**: `academy_service_key`(open.neis.go.kr, data.go.kr 키와 별개) 발급 → `.env` → `collect_places` → `geocode`(좌표 부여). 세분류 매핑은 `app/services/places.py` `CATEGORY_LABELS`.
- 적재 후 `bump_data_version()`이 캐시를 무효화하므로 별도 재시작 불필요(수집 스크립트가 호출).

## 통근권(commute) 운영
1. 목적지 시드: `python -m scripts.seed_commute` (정밀 좌표 필요시 `--geocode`, 카카오 키 필요)
2. 단지 좌표 선행: `python -m scripts.geocode`
3. 통근시간 배치: `python -m scripts.compute_commute` (대중교통은 `--mode transit`)
   - 캐시가 비어도 `/commute/search`는 즉석 추정으로 동작. 배치 후 실측(api)으로 자동 대체.

## 웹푸시(푸시 알림) 설정

관심 단지 **신고가 경신·새 실거래** 알림을 휴대폰/브라우저 푸시로 보냅니다. 유료 서비스 없이 표준 웹푸시(VAPID)를 사용합니다.

설정 절차:
1. 의존성 설치: `pip install -r requirements.txt` (pywebpush 포함).
2. VAPID 키 생성: `python -m scripts.gen_vapid` → 출력된 `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT`(연락 가능한 mailto)를 `.env`에 입력.
3. DB 반영: `python -m scripts.db_upgrade upgrade head` (0010_push 적용).
4. 서버 재기동 후 확인: `GET /push/vapid` → `{"enabled": true, "publicKey": "..."}`.
5. 앱에서 알림(🔔) → "푸시 알림 켜기" → 권한 허용. `POST /push/test`로 본인 기기에 테스트 발송 가능.

동작:
- 수집(스케줄러)에서 신규 실거래·신고가가 감지되면, **로그인 사용자의 관심 단지**에 한해 앱 내 알림과 함께 푸시가 발송됩니다(`notify_transactions` → `push.dispatch_to_account`).
- 푸시는 **HTTPS**에서만 동작합니다(Cloudflare Tunnel 등 외부 도메인 필요). `http://localhost`는 개발용으로 예외 허용됩니다.
- 만료된 구독(404/410)은 자동으로 비활성 처리되어 정리됩니다.
- VAPID 키가 없으면 푸시만 비활성이며 나머지 기능·앱 기동에는 영향이 없습니다(키 게이팅).

주의/한계:
- 비로그인 기기의 구독은 저장되지만, 관심 단지 알림은 **로그인(계정 연결) 기기** 기준으로 발송됩니다. 로그인하면 해당 기기 구독으로도 전달됩니다.
- iOS Safari는 **홈 화면에 추가(PWA 설치)** 후에야 웹푸시가 동작합니다(브라우저 탭 상태에서는 미지원).

## 모니터링(관측성)

무인 운영에서 "조용히 깨짐"을 막기 위한 장치입니다.

무엇을 보나:
- **통합 상태**: `GET /admin/monitor` (X-Admin-Token) — DB 연결, 실데이터 최신 계약일·며칠 지났는지(stale), 최근 작업(수집/지오코딩) 성공·실패·소요, 핵심 카운트(실거래·단지·푸시구독·관심), 연동 활성여부, **경고 목록**과 `ok` 불리언. 관리자 UI(`/admin/ui`)의 "🩺 시스템 상태" 버튼으로도 확인.
- **실행 이력**: `GET /admin/runs?limit=&name=` — 배치별 성공/실패/통계/오류 이력(job_runs).
- **헬스체크**: `GET /health` — DB 핑 + 마지막 수집 시각 + 설정여부(키 값은 노출 안 함). 업타임 모니터(UptimeRobot 등)로 이 URL을 주기 폴링 권장.
- **데이터 신선도/커버리지**: `GET /status/data` — 구별 건수·최신 계약일.

어떻게 경보받나:
- 스케줄러의 수집/지오코딩은 `monitoring.record_job` 으로 감싸져, **실패 시 자동 경보**(`alert`)가 발생합니다.
- 경보 채널: 항상 ERROR 로그. `ALERT_WEBHOOK_URL`(Slack/Discord Incoming Webhook 등) 설정 시 해당 채널로도 발송.
- `SENTRY_DSN` 설정 시 미처리 예외가 Sentry로 수집(스택트레이스·빈도). `pip install -r requirements.txt`에 sentry-sdk 포함.

권장 셋업(최소):
1. `.env`에 `ADMIN_TOKEN` 설정 → `/admin/monitor`로 상태 확인 가능.
2. (선택) `ALERT_WEBHOOK_URL`에 Slack/Discord 웹훅 → 수집 실패 즉시 알림.
3. (선택) `SENTRY_DSN` → 에러 추적.
4. 외부 업타임 모니터로 `/health`를 5~10분 간격 폴링.
DB 반영: `python -m scripts.db_upgrade upgrade head` (0011_jobrun).

## 백업 / 복구

데이터 안전장치입니다. 공공데이터(실거래·청약)는 재수집 가능하지만, **사용자 데이터(관심·커뮤니티·동의이력·푸시구독)**는 백업이 필수입니다.

백업:
- 수동 1회: `python -m scripts.backup` → `BACKUP_DIR`(기본 `backups/`)에 `cheongju_<날짜시각>.dump`(PostgreSQL) 또는 `.sqlite.gz`(SQLite) 생성.
- 자동: 스케줄러가 사이클마다(기본 일 1회) 백업 수행(`SCHEDULER_RUN_BACKUP=true`). 결과는 `/admin/monitor`의 `last_runs.backup`과 `/admin/runs?name=backup`에서 확인.
- 보관주기: 최근 `BACKUP_KEEP`(기본 14)개만 남기고 자동 삭제.
- 실패 시 monitoring 경보(웹훅/로그)로 통지.
- 전제: PostgreSQL은 `pg_dump`가 PATH에 있어야 함(PostgreSQL 클라이언트 설치). 백업 폴더는 가능하면 **다른 디스크/외부 저장소로 주기 복제**(오프사이트) 권장.

복구(⚠️ 현재 데이터 덮어씀):
1. 목록 확인: `python -m scripts.restore --list`
2. 복원: `python -m scripts.restore cheongju_<날짜시각>.dump --yes`
   - PostgreSQL: `pg_restore --clean --if-exists`로 복원.
   - SQLite: 기존 파일을 `.bak`로 옮기고 백업을 해제해 교체.
3. 앱·스케줄러 재기동.

복구 리허설(권장): 분기 1회, 운영과 분리된 임시 DB에 최신 백업을 복원해 정상 적재되는지 점검하세요(백업이 "복원 가능한지"까지 확인해야 진짜 백업).
