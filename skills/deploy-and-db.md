# DB 전환·배포 (skills)

## DB는 환경변수 하나로 갈린다 (로컬 SQLite ↔ 운영 PostgreSQL)
- `DATABASE_URL` **미설정 → SQLite**(`./cheongju_local.db`). 설치 0, `python run.py` 그대로. **로컬 개발/테스트는 이걸로 충분.**
- `DATABASE_URL` 설정 → 그 DB 사용. `postgres://`·`postgresql://` 는 **자동으로 `postgresql+psycopg://`(psycopg3)로 정규화**되므로 관리형 DB(Neon·Supabase·RDS·Heroku) URL을 그대로 붙여도 됨.
- 코드는 DB 비종속(범용 타입 + JSON). 같은 모델이 두 DB에서 동작.

## '진짜 Postgres'로 점검(설치 없이, 선택)
```
docker compose up -d
export DATABASE_URL=postgresql://cheongju:cheongju@localhost:5432/cheongju
python run.py
docker compose down       # -v 추가 시 데이터까지 삭제
```
일상 개발은 SQLite, **배포 직전 한 번**만 Postgres로 확인하는 흐름을 권장(미세한 방언 차이 점검).

## 스키마 관리: 첫 부팅은 create_all, 이후엔 Alembic
- 첫 실행은 `init_db()`의 `create_all`이 없는 테이블을 자동 생성(SQLite·Postgres 공통). 바로 뜬다.
- **운영에서 스키마를 바꿀 땐 Alembic**으로 안전하게:
  1. (create_all로 이미 만든 DB라면 1회) 베이스라인 표시: `alembic stamp head`
  2. 모델 변경 후 자동생성: `alembic revision --autogenerate -m "설명"`
  3. 적용: `alembic upgrade head`  (롤백: `alembic downgrade -1`)
- `migrations/env.py`가 app 설정의 DB URL + `Base.metadata`를 읽으므로, 로컬(SQLite)·운영(PG) 동일 명령으로 동작(SQLite는 batch 모드 자동).
- 새 모델/컬럼을 추가하면 **반드시 마이그레이션을 생성**할 것(운영 DB는 create_all에 의존하지 말 것).

## 운영 배포 체크(다음 단계들)
- 앱서버: `gunicorn -k uvicorn.workers.UvicornWorker app.main:app -w <코어수>` + 리버스프록시(Nginx)·HTTPS.
- 컨테이너화(Dockerfile) + 환경변수로 시크릿 관리. `run.py`는 개발용.
- 수집 배치 스케줄러(cron/Celery beat)로 증분 적재. 모니터링(헬스체크·로그·Sentry)·백업.

## 관리자 API/스케줄러(운영)
- 관리자 API: `ADMIN_TOKEN` 설정 시 활성. `X-Admin-Token` 헤더 필요.
  - `GET /admin/status` 좌표 커버리지(전체 단지/지오코딩/누락/%).
  - `POST /admin/geocode?limit=0` 지오코딩(백그라운드). `POST /admin/collect?geocode=true` 수집+지오코딩.
  - 브라우저 UI: `GET /admin/ui`(토큰 입력 후 버튼). 토큰은 서버에 저장하지 않음.
  - 동시 실행 방지: in-process 락(409 if 실행중).
- 스케줄러: `python -m scripts.scheduler`(의존성 없는 루프). 웹 워커와 분리된 **단일 프로세스**로만 실행.
  - `.env`: SCHEDULER_INTERVAL_HOURS(기본24), SCHEDULER_RUN_COLLECT. 첫 사이클 즉시 실행 후 주기 반복.
- run.py도 수집 후 자동 지오코딩(AUTO_GEOCODE) 수행 — 개발/단일 인스턴스용.


## 스키마 마이그레이션 (일원화)
- 권위 소스: **Alembic**. env.py 의 `target_metadata = Base.metadata`, URL 은 앱 설정(effective_database_url) 주입.
- 이력(현행): `0001_listings` → `0002_baseline`(나머지 전체 생성, checkfirst 멱등) → `0003_tx_alerts`(알림) → `0003_tx_cancel`(해제) → `0004_consents`(대출 동의) → `0005_complex_meta` → `0006_gongsi` → `0007_search_index` → `0008_tx_trade_method` → `0009_commute` → `0010_push`(웹푸시 구독) → `0011_jobrun`(작업 실행 이력). 모든 추가형 마이그레이션은 `inspect().has_table` 가드로 멱등(fresh DB는 create_all 로 이미 생성됨), 타입 portable.
- 운영 배포 순서: 이미지 빌드 → `python -m scripts.db_upgrade`(=upgrade head) → 앱 롤아웃.
- 기존 create_all DB 편입: `python -m scripts.db_upgrade stamp head` (이력만 head 로 표시, 스키마 변경 없음).
- 이후 변경: 모델 수정 후 `alembic revision --autogenerate -m "..."` → 생성된 DDL 검토 → 커밋 → 배포 시 upgrade head.
- 무중단 원칙: 가능한 한 추가형(additive) 변경(컬럼 추가→코드 배포→정리). 파괴적 변경은 2단계로.
- dev(SQLite)는 create_all + _ensure_columns 로 빠른 시작(스키마는 baseline 과 동일). render_as_batch 로 SQLite ALTER 한계 보완.


## 관측성 (데이터 신선도·로깅)
- `GET /health`: 라이브니스 + DB 핑(db_ok) + data_version + last_collect_at + 키 설정여부(값 비노출). 모니터/LB 용.
- `GET /status/data`: 공개 집계(개인정보 없음) — 최신 계약일(data_as_of)·총 거래수·구별 건수/최신일·지오코딩 커버리지·마지막 수집(시각/경과/stale)·data_version. UI '데이터 기준' 배너도 사용.
- 영속 메타: `app_meta`(키-값). `app/services/appmeta.py`(get/set/get_int/get_json/set_json). 알림 커서·last_collect 등.
- 수집(collect_live/fixtures) 종료 시 `last_collect`(at/mode/new/seen) 기록 → 신선도 노출. STALE_HOURS(기본 36h) 초과 시 stale.
- 로깅: `app/core/logging.py setup_logging()`이 일관 포맷 + httpx/httpcore INFO 소음 억제. 요청 타이밍 미들웨어가 메서드/경로/상태/지연 1줄 로깅(/health·/uploads 제외).
- 운영 점검: 배포 후 `/health`(db_ok=true), `/status/data`(stale=false, data_as_of 최신) 확인.


## 레이트리밋(어뷰징/스팸 방어)
- app/core/ratelimit.py(인프로세스 고정 윈도) + main.py 미들웨어. 분당 IP 기준, 버킷별 한도(.env).
- 대상: 글쓰기/댓글/신고/검색/매물등록/로그인. 초과 시 429 + Retry-After. 한도 0이면 해당 버킷 무제한.
- 클라이언트 IP: X-Forwarded-For 첫 홉 우선(프록시 뒤) → request.client.host. 프록시가 신뢰 가능한 환경에서만 XFF 신뢰.
- 다중 워커/인스턴스는 프로세스별 적용(전역 아님). 더 엄격한 전역 제한은 공유 저장소(Redis)로 교체 — 캐시와 동일 구조.
- 테스트는 RATE_LIMIT_ENABLED=false 로 결정성 확보.


## 웹푸시 (VAPID) — services/push.py · api/push.py
- 표준 웹푸시(VAPID). 유료 서비스 불필요. `pywebpush` **지연 import**(미설치/키 없어도 앱 기동).
- 활성 조건: `settings.push_enabled`(= vapid_public_key & vapid_private_key 둘 다). 없으면 모든 발송이 no-op.
- 모델 `PushSubscription`(device_id 항상, account_id 로그인 시) — endpoint 기준 멱등 upsert, 만료(404/410) 시 `disabled=True` 자동 정리, 연속 실패 8회 시 비활성.
- 발송: `push.dispatch_to_account(db, account_id, payload)` — 계정 직접 + 연결된 device_id 구독 모두. notify_transactions가 알림 생성 시 호출(실패해도 수집·알림 불영향, try/except).
- API: `/push/vapid`(공개키·활성여부) · `/push/subscribe`(브라우저 구독 저장) · `/push/unsubscribe` · `/push/test`.
- 서비스워커는 백엔드가 `/sw.js`(app/web/sw.js)로 서빙(스코프=루트). 프런트는 알림함 'PushToggle'에서 권한요청→구독→저장.
- 키 생성: `python -m scripts.gen_vapid`(py_vapid). HTTPS 필수, iOS는 PWA 설치 후 동작.
- 새 알림 타입 추가 시: notify에서 payload(title/body/url)만 구성해 dispatch에 넘기면 됨(채널 로직 불변).

## 관측성 (모니터링·경보) — services/monitoring.py
- `record_job(db, name, fn)`: 배치를 감싸 `JobRun`(running→ok/fail·소요·통계·오류) 기록 + 실패 시 `alert` + 재발생. 스케줄러는 try/except로 감싸 계속 진행. 성공 시 결과 반환.
- `alert(subject, body)`: 항상 ERROR 로그 + `ALERT_WEBHOOK_URL` 설정 시 웹훅(Slack=text/Discord=content 동시 전송). 키 없으면 로그만.
- `system_status(db)`: DB핑·실데이터 신선도(stale_days vs `data_stale_days`)·최근 실행(KNOWN_JOBS)·핵심 카운트·연동 활성여부·**경고 목록·ok 불리언**. 모니터링 폴링 1회로 전체 파악.
- 스케줄러(`scripts/scheduler.py`)가 collect_live·geocode·backup을 record_job으로 감쌈. geocode 키 없음(GeocodeKeyMissing)은 실패 아님 → skip 처리(경보 안 함).
- 에러 모니터링: `SENTRY_DSN` 설정 시 main 기동에서 sentry_sdk 초기화(지연 import, 미설치/미설정 무동작).
- 관리자: `GET /admin/monitor`(system_status) · `/admin/runs`(이력) — ADMIN_TOKEN. /admin/ui 버튼 제공.
- 새 배치 추가 시: `record_job(db, "<name>", fn)`으로 감싸고 모니터링에 보이게 하려면 monitoring.KNOWN_JOBS에 이름 추가.

## 백업 / 복구 — scripts/backup.py · scripts/restore.py
- 백업: PostgreSQL=`pg_dump -Fc`, SQLite=gzip 복사. `BACKUP_DIR`에 `cheongju_<ts>.(dump|sqlite.gz)`, `BACKUP_KEEP`개만 보관(자동 정리). record_job("backup")로 기록·경보.
- 스케줄러가 사이클마다 백업(`SCHEDULER_RUN_BACKUP`). `parse_db_url`은 외부의존 없는 순수 함수(테스트 가능).
- 복구: `python -m scripts.restore --list` → `python -m scripts.restore <파일> --yes`(pg_restore --clean --if-exists / SQLite 교체). ⚠️ 현재 데이터 덮어씀.
- 전제: pg_dump/pg_restore가 PATH에. 백업 폴더는 오프사이트 복제 권장. 분기 1회 복구 리허설.

## 배포 자가진단 — scripts/doctor.py
- `python -m scripts.doctor`: 설정·DB·핵심 테이블(마이그레이션)·지역코드 실조회(MOLIT 1회)·데이터 신선도/건수·연동 키·백업 준비(pg_dump·쓰기권한)·관리자 토큰을 ✅/⚠️/❌로 점검. ❌ 있으면 종료코드 1. `--skip-live`로 외부호출 생략.
- monitoring.system_status·MolitClient·CHEONGJU_DISTRICTS 재사용. **배포 직후 가장 먼저 실행**해 그동안 추가한 백엔드(푸시·모니터링·백업·수집)를 한 번에 확인.
