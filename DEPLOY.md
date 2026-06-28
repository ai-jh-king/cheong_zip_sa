# DEPLOY — 프로덕션 배포·운영 런북

> 실제 서비스 배포/운영에 필요한 절차. 컨테이너 빌드·실행은 **운영 머신(Docker 보유)** 에서 수행.
> ⚠️ 정직한 한계: 개발 샌드박스(네트워크 X)에선 이미지 빌드·실행을 검증하지 못함 → 아래 절차로 운영 머신에서 확인.

## 1. 아키텍처
```
[사용자] → HTTPS → [리버스 프록시 Nginx/Caddy] → web:8000 (uvicorn, 워커 N개)
                                                  ├─ scheduler (단일 프로세스, 수집·백업)
                                                  └─ db (PostgreSQL)
```
- **web**: 무상태 → 여러 워커/인스턴스 OK(스케줄러가 앱 안에서 안 돎).
- **scheduler**: `python -m scripts.scheduler` **항상 1개만**(중복 수집 방지).
- **db**: PostgreSQL(운영). 개발은 SQLite 폴백.

## 2. 사전 준비
- 도메인 + TLS 인증서(Let's Encrypt 등).
- `data.go.kr` 키 **활용신청 승인**(실거래·청약 데이터셋별), 네이버 지도 키(도메인 등록), (선택) 금융/로그인/Sentry 키.
- `.env` 작성 — **전체 목록·설명은 `.env.example` 이 정본**. 아래는 배포에 특히 중요한 것.

## 3. 필수/중요 환경변수
| 키 | 필수 | 설명 |
|---|---|---|
| `JWT_SECRET` | ✅ | 세션 토큰 서명키. **반드시 강한 무작위값**(미설정 시 로그인 취약). |
| `DATABASE_URL` | ✅(운영) | 예 `postgresql://user:pw@db:5432/cheongju`. 미설정 시 SQLite 폴백(운영 비권장). |
| `CORS_ORIGINS` | ✅(운영) | 콤마구분. 예 `https://도메인,capacitor://localhost,https://localhost`. 미설정 시 `*`(개발용). |
| `APP_ENV` | 권장 | `production` 권장. |
| `ADMIN_TOKEN` | 권장 | 관리자 API 토큰. 미설정 시 관리자 API 비활성. |
| `MOLIT_SERVICE_KEY` | 기능 | 실거래 수집(없으면 실데이터 X). |
| `APPLYHOME_SERVICE_KEY` | 기능 | 청약·분양. |
| `NAVER_MAP_CLIENT_ID`(+secret) | 기능 | 지도 표시. |
| `VAPID_*`(공개/비공개) | 기능 | 웹푸시(.env.example 참조). |
| `FINLIFE_API_KEY`·`HF_API_KEY`·`SEOMIN_API_KEY` | 기능 | 대출 상품/정책. |
| `SENTRY_DSN` | 선택 | 에러 모니터링 활성. |
| `WEB_CONCURRENCY` | 선택 | web 워커 수(기본 2). |
| `WEB_DIR` | 선택 | 컷오버 시 `frontend/dist`(→ `CUTOVER.md`). 기본=레거시. |

> 🔐 비밀은 **이미지에 넣지 말 것**. `.env`/시크릿 매니저로 주입(.dockerignore가 .env 제외).

## 4. 빌드 & 실행 (운영 머신)
> 이미지는 **멀티스테이지**(프런트 Vite 빌드 → 백엔드 런타임에 `dist` 포함, `WEB_DIR=/app/frontend/dist` 고정) — **컨테이너가 dist를 서빙(컷오버 확정)**. 빌드 머신에 Docker만 있으면 됨(별도 npm 단계 불필요).
```
# 1) 이미지 빌드 + 기동(web + scheduler + db)
docker compose -f docker-compose.prod.yml up -d --build

# 2) 최초/배포 시 DB 마이그레이션
docker compose -f docker-compose.prod.yml run --rm web alembic upgrade head

# 3) 헬스 확인
curl -s localhost:8000/health        # ok 여야 함
```
> 단일 컨테이너만 쓸 경우: `docker build -t cheongju-app . && docker run -p 8000:8000 --env-file .env cheongju-app`

## 5. 리버스 프록시 / HTTPS (예: Nginx)
```nginx
server {
  server_name your-domain;
  location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host; proxy_set_header X-Forwarded-For $remote_addr; }
  location /assets/ { proxy_pass http://127.0.0.1:8000; expires 1y; add_header Cache-Control "public, immutable"; }  # 컷오버(dist) 시
  # TLS는 certbot/Caddy 등으로 종단
}
```
- 이미지가 dist를 서빙하므로 `/assets`(해시 파일) 블록이 유효(컷오버 확정). 레거시 폴백 시엔 무해.

## 6. 배포 전 점검 체크리스트
- [ ] `python -m scripts.doctor` — 키/DB/설정 누락 0
- [ ] `pytest` — 회귀 green
- [ ] `python -m scripts.verify_region_codes` — 지역코드·키 정상
- [ ] `python -m scripts.run_collect live` 1회 — 실거래 적재 확인(`/status/data`)
- [ ] 백업 1회 실동작(`scripts` 백업) + 복구 절차 확인(OPERATIONS.md)
- [ ] 웹푸시 발송 1회(구독→발송→수신)
- [ ] `/health` ok, `/admin/monitor` 정상, Sentry 수신(설정 시)
- [ ] `CORS_ORIGINS`·`JWT_SECRET`·`ADMIN_TOKEN` 운영값으로 설정됨

## 7. 운영
- **스케줄러 단일 원칙**: `scheduler` 서비스는 절대 scale 금지(중복 수집). 주기 `SCHEDULER_INTERVAL_HOURS`.
- **백업/복구**: 정기 `pg_dump` + 복구 리허설(OPERATIONS.md).
- **모니터링**: `/health`·`/status/data`·`/admin/monitor`·Sentry. 수집 실패·신선도 경보 확인.
- **로그**: 컨테이너 stdout(요청 타이밍 미들웨어 포함).
- **롤백**: 이전 이미지 태그로 `up -d`. 컷오버 롤백은 `unset WEB_DIR`(CUTOVER.md).
- **레이트리밋**: 미들웨어 내장. 공공 API 일일한도 → 자체 DB 캐싱·증분 수집 유지.

## 8. 보안 체크
- [ ] `CORS_ORIGINS` 실제 도메인+앱 origin으로 좁힘(기본 `*` 금지)
- [ ] `JWT_SECRET` 강한 무작위, `ADMIN_TOKEN` 설정
- [ ] 컨테이너 **비루트**(Dockerfile에서 appuser) — 적용됨
- [ ] `.env` 비밀 이미지 미포함(.dockerignore) — 적용됨
- [ ] TLS 종단(프록시), 내부는 사설망

## 9. 미해결/후속
- 컷오버(프런트 `dist` 서빙)는 `CUTOVER.md` 절차 — 빌드 검증 후.
- 정적 자산 CDN·캐시 헤더(운영 성능)는 프록시에서.
- 네이티브 앱 배포는 `MOBILE_APP_STRATEGY.md`·`CAPACITOR.md`.

## PWA 앱 셸 캐싱 / 오프라인 / 업데이트 (v1.93+)

서비스워커(`frontend/public/sw.js`)가 앱 셸을 런타임 캐싱한다. **빌드 도구 의존성 없음**(Workbox/플러그인 미사용) — Vite 해시 자산을 이용한 수제 SW.

**캐싱 전략**
- 페이지 이동(navigate): **네트워크 우선** → 실패 시 캐시된 셸(`/`) → `offline.html`.
- 정적 자산(`/assets/*`·`/icons/*`·`/manifest.webmanifest`): **캐시 우선 + 백그라운드 갱신**. Vite 자산은 파일명 해시가 있어 캐시 우선이 안전(새 빌드=새 파일명=새로 받음).
- **그 외(API 등)는 가로채지 않음** → 항상 네트워크. 시세·실거래 등 데이터는 절대 캐시하지 않는다(신선도·왜곡 방지). ※ API가 같은 오리진이어도 `/assets`·`/icons`·manifest만 캐시하므로 안전.

**업데이트 흐름**
- 온라인에서 재방문/새로고침 시 navigate가 네트워크 우선이라 최신 `index.html`(새 자산 해시)을 받고 새 자산이 자동 반영된다. 별도 조치 없이도 업데이트가 흐른다.
- 화면을 계속 켜둔 사용자에게는 **새 버전 배너**("새 버전이 준비됐어요 · 새로고침")가 뜬다(앱 내 `swUpdate`). 단, 이 배너는 **sw.js 파일이 바뀌어 브라우저가 새 SW를 감지할 때** 발화한다.

**운영 규칙(중요)**: 새 버전을 배포할 때 **`sw.js`의 `var VERSION` 값을 올린다**(예: `v2`→`v3`).
- 효과 ①: 구버전 셸 캐시가 activate에서 정리된다(고아 자산 제거).
- 효과 ②: sw.js 바이트가 바뀌어 브라우저가 새 SW를 감지 → 사용자에게 업데이트 배너가 뜬다.
- (콘텐츠/자산만 바뀐 배포는 VERSION을 안 올려도 네트워크 우선으로 다음 로드에 반영되지만, 배너는 안 뜬다.)

**확인**: `npm run build` → `WEB_DIR=dist`로 서빙 → 브라우저 접속(SW 등록) → DevTools>Application>Service Workers/Cache Storage에서 `cj-shell-vN` 확인 → Network>Offline 후 새로고침 시 앱 셸/오프라인 페이지 표시. (샌드박스에선 빌드·런타임 검증 불가 — 운영자 확인 필요)

## 검색 인덱스(pg_trgm) — 운영 주의 (0016)

통합 검색은 선두 와일드카드 `LIKE '%q%'`라, **PostgreSQL에서 pg_trgm GIN 인덱스**(마이그레이션 `0016_search_trgm`)로 가속한다.
- 마이그레이션이 `CREATE EXTENSION IF NOT EXISTS pg_trgm` 을 실행한다. **관리형 DB(RDS/Cloud SQL 등)는 확장 생성 권한이 필요**할 수 있다(슈퍼유저 또는 허용목록). 권한이 없으면 마이그레이션이 실패하므로, 사전에 DBA가 확장을 활성화하거나 권한을 부여할 것.
- **SQLite는 자동 스킵**(no-op) — 개발/소규모는 스캔 폴백으로 동작(인덱스 없음).
- 대형 테이블 무중단 생성이 필요하면 마이그레이션 대신 `CREATE INDEX CONCURRENTLY ... USING gin (col gin_trgm_ops)` 를 수동 실행(트랜잭션 밖). 컬럼: transactions.complex_name/dong_name, listings.title/complex_name/dong_name.
- 트라이그램은 3글자 이상에서 선택도가 좋다(1~2글자 검색은 여전히 스캔에 가깝지만 다른 필터·limit로 제한됨).

## 초기 로딩·전송 최적화 (v1.105)

번들에 무거운 라이브러리가 없다(react+react-dom, 차트는 SVG, 지도 SDK는 외부 스크립트). 그래서 초기 로딩의 핵심은 코드 분할이 아니라 **압축·캐시**다.
- **gzip 압축**: 앱에 `GZipMiddleware`(minimum_size=600) 적용 — JS/CSS/HTML/JSON 전송량 약 65~70%↓. uvicorn/FastAPI가 직접 서빙할 때 효과.
- **해시 자산 캐시**: Vite 산출물 `/assets/*`는 내용 해시 파일명이라 `Cache-Control: public, max-age=31536000, immutable` 로 서빙(재방문 즉시). `index.html`·`sw.js`·manifest·아이콘은 `no-cache`(업데이트 즉시 반영).
- **vendor 청크 분리**: Vite `manualChunks`로 React를 별도 청크로 → 앱 코드만 바뀌면 React 청크는 캐시 유지.
- ⚠️ **운영 권장**: 앞단에 nginx/CDN(CloudFront 등)을 두면 압축·캐시·브로틀리를 더 효율적으로 처리하고 정적 자산을 엣지에서 서빙할 수 있다. 앱 레벨 gzip은 그게 없을 때의 안전한 기본값.
- 측정: 머신에서 `cd frontend && npm run build` → 청크 크기 확인. 브라우저 DevTools Network에서 `content-encoding: gzip`·자산 `cache-control` 확인.

## Render 배포 — 단계별 (웹/PWA 출시)

> 전제: GitHub에 코드 푸시 가능. `render.yaml`(블루프린트) 동봉 — 웹+Postgres+크론을 한 번에 생성.

**1. GitHub에 올리기**
```
git add . && git commit -m "deploy: render ready" && git push
```

**2. Render에서 블루프린트로 생성**
- render.com 가입(GitHub 연동) → New + > **Blueprint** > 이 저장소 선택 > **Apply**
- `render.yaml`이 자동으로 ① 웹 서비스 ② PostgreSQL ③ 매일 수집 크론을 만든다.
- `JWT_SECRET`·`ADMIN_TOKEN`은 Render가 자동 생성. `DATABASE_URL`도 자동 연결.

**3. 비밀값 직접 입력**(sync:false 항목)
- 웹 서비스 > Environment 에서:
  - `MOLIT_SERVICE_KEY` = 발급받은 키
  - `CORS_ORIGINS` = 실제 접속 도메인(예: `https://cheongju.onrender.com` 또는 연결한 커스텀 도메인)
- 크론 서비스에도 `MOLIT_SERVICE_KEY` 동일 입력.

**4. 마이그레이션은 자동**
- 웹 서비스의 `preDeployCommand: python -m scripts.db_upgrade` 가 배포마다 자동 실행(head 0016).

**5. 첫 데이터 수집**(최초 1회는 수동 트리거 권장)
- 크론 서비스 > **Trigger Run** 으로 즉시 1회 수집 → 이후는 매일 04:00(KST) 자동.
- 좌표(지도 마커)는 별도 1회: 로컬에서 `scripts.geocode` 돌리거나 크론/Job으로 추가.

**6. 확인**
- 웹 서비스 URL 접속 → 시세·지도에 실데이터. `/health` 200 확인.
- 출시 안전점검: 로컬에서 동일 env로 `python -m scripts.preflight` FAIL 0 권장.

**7. 도메인(선택)**
- 웹 서비스 > Settings > Custom Domain 에 보유 도메인 연결(HTTPS 자동). 연결 후 `CORS_ORIGINS`도 그 도메인으로 갱신.

**비용 메모**: 무료 티어는 15분 미사용 시 슬립(첫 요청 지연). 실사용 시작하면 웹 Starter(~$7/월)+Postgres(~$6/월)로 업그레이드 권장. 크론은 유료 → 무료로만 시작할 거면 render.yaml에서 cron 블록을 빼고 수집은 수동/대안으로.

**PWA(완전한 앱 체험)**: 배포된 URL을 폰 브라우저에서 열고 "홈 화면에 추가" → 전체화면 앱처럼 사용(설치형). 스토어 등록(네이티브)은 이후 단계.
