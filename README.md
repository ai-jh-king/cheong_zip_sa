# 청주 부동산 정보 플랫폼

충북 **청주시**(상당·서원·흥덕·청원 4개 구) 실수요자를 위한 부동산 정보 서비스.
실거래 시세·추이·청약·뉴스·정책·대출·세금을 **한 화면에서** 비교하고, 사용자 커뮤니티까지
하나로 묶었습니다. 모든 데이터는 **공식 공공 API**에서만 가져오며, 추정·예시는 항상 구분 표기합니다.

> 응답·UI·문서는 모두 한국어입니다. 키가 없어도 모의데이터로 즉시 실행되어 화면을 확인할 수 있습니다.

---

## 설계 철학 — "왜곡 없음(No Distortion)"

이 프로젝트의 1순위 원칙입니다. 돈을 받고 운영하는 서비스라는 전제로, 데이터를 절대 지어내지 않습니다.

- **공식 소스만**: 국토교통부 실거래가, 한국부동산원 청약홈, 금감원·주택금융공사 등 공공 API와 정식 제휴만 사용. 타 서비스 스크래핑 금지.
- **추측 금지**: 외부 응답 필드를 추측하거나 0으로 채우지 않음. 없는 값은 `null` + "표본 부족" 사유. 예시·모의데이터는 `is_sample`/화면 배지로 항상 구분.
- **원본 보존**: 모든 거래에 `raw_payload`(원본)·`source`(출처)·`collected_at` 저장.
- **참고용 고지**: 실거래·대출·세금 결과는 "참고용 추정치"이며 금융/세무 자문이 아님을 화면에 상시 표기. "승인/최저금리 보장" 등 단정 금지.
- **개인정보 최소화**: 기본은 익명 `device_id`. 민감정보(소득·신용)는 동의 후 비중앙저장(세션/기기) 원칙.
- **설정값 분리**: 규제·요율(LTV/DSR·세금·중개보수·캐시 TTL)은 하드코딩 금지 → 설정/룰로 분리해 정책 변경 시 값만 수정.

---

## 주요 기능

### 시세·분석
- **통합 대시보드**: 청주 평균 매매/전세/월세 요약, 전월·전년 대비 등락폭, 구별 비교, 대장 아파트·최신 실거래·맞춤 추천 위젯.
- **시세 조회 & 통합검색**: 지역(구·동)·거래유형·면적·기간 필터. 단지/지역/매물을 한 번에 찾는 통합검색.
- **시세 추이 & 등락폭**: 단지·지역별 시계열, 매매가 대비 전세가율(갭), 거래량 추이. 평형(면적대)별 분리 표시.
- **단지 상세**: 면적별 시세(최신/중앙값/고점/저점·전세가율·평단가·타임라인), 지도 핀, 인근 인프라(POI), 대출 시뮬레이션 통합.
- **지역 비교 & 랭킹**: 구·동 나란히 비교, 평단가/가격대 밴드별 랭킹.
- **지도/히트맵**: 구 단위 평단가 마커(좌표 없이도 표시) + 단지 단위(지오코딩 시) 토글.

### 청약·뉴스·대출·세금
- **청약·분양**: 분양 예정/진행 단지, 주택형별 공급·분양가, 경쟁률.
- **뉴스 & 정책**: "청주 부동산" 뉴스 피드(제목·요약·출처링크만, 원문 전재 금지)와 정책 요약.
- **대출 추천**: LTV·DSR을 함께 적용한 한도 산출, 정책대출(디딤돌·보금자리)·은행 주담대/전세·서민금융 비교, 상환방식별 월상환액 시뮬레이션. 규제값은 설정으로 분리.
- **세금/총비용**: 취득세·중개보수 등 매입 총비용 추정(요율 분리).

### 사용자 기능
- **개인화**: 관심 단지/지역, 최근 본 단지, 저장 검색, 내 동네, 맞춤 추천, 대출 프로필. 익명 `device_id`로 시작해 **로그인 시 기기 데이터 자동 승계(union)**.
- **소셜 로그인**: 카카오·네이버 OAuth + 개발용 로그인. 외부 의존 없는 표준 라이브러리 JWT 세션.
- **매물 등록(UGC)**: 「중개대상물 표시·광고 명시사항」 국토부 고시(2025.1.1 시행) 항목 준수. 사진 업로드(로컬/S3 추상화).
- **커뮤니티 게시판**: 카테고리(자유·질문·정보·매물상담·지역소식), 이미지 첨부, **@단지 연결**(글→단지 시세로 이동), 좋아요·신고(누적 자동숨김), **대댓글·댓글 정렬·글/댓글 수정**, **이번 주 베스트**, **내 활동**(내 글·댓글), **스크랩(북마크)**, **작성자 프로필·활동 배지**.
- **알림**: 내 글에 댓글, 내 댓글에 답글이 달리면 헤더 벨에 미읽음 배지 → 알림 패널 → 해당 글로 이동.

### 운영
- **관리자 API/UI**: 토큰 게이트 상태 점검·수집·지오코딩 트리거.
- **스케줄러**: 독립 실행형 주기 수집(증분).

---

## 기술 스택 & 아키텍처

**"1 백엔드 · N 프런트"** — 시세 집계·대출 한도·세금 등 비즈니스 로직은 전부 백엔드에 두고, 웹/앱은 표시·입력만 담당합니다.

| 영역 | 스택 |
|---|---|
| 백엔드 | Python · FastAPI · SQLAlchemy 2.0 (계층: `api / services / sources / pipeline / models / data`) |
| 프런트 | **정본: `frontend/src/main.jsx`**(React 18 + Vite → `dist/`, PWA·스토어용). 레거시 `app/web/index.html`(Babel CDN)은 **동결**(개발 폴백). 컷오버 구성 완료(Dockerfile 멀티스테이지·`WEB_DIR`), 운영 빌드 검증은 개발 머신에서 |
| DB | 기본 SQLite(설치 0) ↔ `DATABASE_URL` 설정 시 PostgreSQL. Alembic 마이그레이션 |
| 캐시 | 인프로세스 TTL 캐시(single-flight·negative). 외부 호출 + 시세 집계에 적용 |
| 외부 | 국토부 실거래 8종, 청약홈, 금감원 finlife, 주택금융공사 HF, 서민금융, 네이버/카카오 지도·POI, 네이버 검색(뉴스) |

데이터 흐름:
```
공공 API ──(레이트리밋·재시도·정규화)──> 자체 DB 적재(증분·dedup) ──> 집계(캐시) ──> REST API ──> 웹/앱
```
외부 API를 매 요청마다 직접 부르지 않고 **자체 DB에 캐싱**합니다. 시세 집계는 **데이터 버전당 1회만 계산**하고 이후 요청은 캐시에서 제공합니다.

---

## 빠른 시작

키가 없어도 즉시 동작합니다(모의데이터). `python run.py` 한 줄이면 의존성 자동 설치 → DB 생성 → 수집 → 서버 기동까지 진행됩니다.

```bash
python run.py
# 윈도우에서 python 이 안 되면:  py run.py
```
실행 후 `http://localhost:8000` 에서 UI, `http://localhost:8000/docs` 에서 API 문서를 볼 수 있습니다. 종료는 Ctrl+C.

```bash
python run.py --refresh     # 기존 적재 무시하고 재수집
python run.py --no-install  # 의존성 자동설치 건너뛰기
```

**실데이터로 보려면** `.env`에 `MOLIT_SERVICE_KEY`(공공데이터포털 디코딩 키)를 넣고 `python run.py --refresh`.
지도/좌표는 1회 `.env`에 네이버/카카오 키 입력 후 `python -m scripts.geocode`.

> 401 인증 오류는 거의 항상 serviceKey 문제입니다. `python -m scripts.verify_region_codes` 로 진단하세요(데이터셋 활용신청·디코딩 키·승인 지연·공백 확인). 실패해도 앱은 모의데이터로 정상 구동됩니다.

---

## 환경 변수(.env)

`.env.example`를 복사해 채웁니다. 핵심만:

| 키 | 용도 |
|---|---|
| `MOLIT_SERVICE_KEY` | data.go.kr 키. **이 키 하나로** 실거래 + 청약홈 + HF + 서민금융 공통(각 데이터셋 활용신청만) |
| `NAVER_MAP_CLIENT_ID/SECRET` | 지도 + 지오코딩(네이버 우선) |
| `KAKAO_REST_API_KEY` | 인근 POI/중개업소 반경 검색(카카오) |
| `NAVER_SEARCH_CLIENT_ID/SECRET` | 뉴스 검색 |
| `FINLIFE_API_KEY` | 은행 금리(금감원 금융상품 한눈에) |
| `DATABASE_URL` | 비우면 SQLite, 채우면 PostgreSQL |
| `KAKAO_LOGIN_REST_KEY` / `NAVER_LOGIN_*` | 소셜 로그인 |
| `STORAGE_*`, `ADMIN_TOKEN`, `SCHEDULER_*` | 사진 스토리지(S3)·관리자·스케줄러 |

규제 파라미터(LTV/DSR·세금·중개보수)와 캐시 TTL도 설정으로 분리되어 있어 정책 변경 시 값만 수정합니다.

---

## 운영
설치·실행·배포·모니터링·장애대응은 **[OPERATIONS.md](OPERATIONS.md)** 에 정리되어 있습니다(운영자 필독).

## 단지 기본정보 보강(K-apt)
공동주택관리정보(K-apt) 공개 API로 단지의 세대수·동수·사용승인일·난방·연면적·시공사·주차를 보강합니다(아파트 한정).
`.env`의 `KAPT_LIST_URL/KAPT_INFO_URL`을 Swagger로 확정해 입력하고 `python -m scripts.enrich`(또는 `/admin/enrich`)로 실행합니다.
미설정·미매칭 항목은 채우지 않고 **null로 둡니다(날조 금지)**. 단지 상세에는 공시가격(공식 CSV)·학군(인근 학교 통학 접근성, 거리 기준)도 함께 노출됩니다.

## 법적 고지(개인정보처리방침·이용약관)
`app/web/legal/`의 템플릿 문서를 `/legal/{privacy|terms}`로 제공하고, 화면 푸터·대출 동의 화면에서 확인할 수 있습니다.
대출 민감정보는 **서버에 저장하지 않으며**, '저장' 선택 시 본인 브라우저에만 보관됩니다. 동의 시 버전·시각을 `Consent`에 기록합니다.
> 문서는 템플릿이며 시행 전 개인정보/법무 전문가 검토가 필요합니다.

## 레이트리밋
글쓰기·댓글·신고·검색·로그인·매물등록에 분당 IP 기준 레이트리밋을 적용합니다(초과 시 429 + Retry-After). 한도는 `.env`로 조정하며, 0이면 해당 버킷 무제한입니다.

## 관측성
- `GET /health` — 라이브니스 + DB 핑 + 데이터 신선도(값 노출 없이 설정여부만).
- `GET /status/data` — 최신 계약일·구별 커버리지·마지막 수집 경과·지오코딩 커버리지(집계만, 공개).
화면 상단에 "데이터 기준 / N일 전 갱신"이 표시되고, 수집이 오래 지연되면 경고로 바뀝니다.

## 테스트
```bash
pip install -r requirements.txt
pytest                       # 전체 테스트
```
순수 로직(대출·세금·정규화·집계 캐시)과 API(원자 카운터·스크랩·스모크)를 검증합니다.
테스트는 버리는 SQLite 를 쓰고 외부 API 를 호출하지 않습니다. push/PR 마다 GitHub Actions(CI)가 자동 실행합니다.

## DB 마이그레이션(운영)

운영/스테이징은 **Alembic**이 스키마의 단일 권위 소스입니다(개발 SQLite는 빠른 `create_all`).

```bash
python -m scripts.db_upgrade            # alembic upgrade head (스키마 최신화)
python -m scripts.db_upgrade current    # 현재 리비전
python -m scripts.db_upgrade stamp head # 기존 create_all DB 를 이력에 편입
```
배포 순서: 빌드 → `db_upgrade`(upgrade head) → 앱 롤아웃. DB URL은 `.env` 한 곳에서 관리합니다.
베이스라인 마이그레이션은 모델 메타데이터에서 생성되어 `create_all` 결과와 스키마가 동일하며, 기존 DB에서도 멱등(no-op)으로 안전하게 head까지 올라갑니다.

---

## 프로젝트 구조

```
app/
  main.py                FastAPI 앱 + 라우터 등록 + UI("/") 서빙
  core/
    config.py            .env 설정, effective_database_url(SQLite↔PG), 캐시 TTL
    cache.py             TTL 캐시 + 데이터 버전 기반 집계 캐시(stat_cached)
    security.py          표준 라이브러리 JWT(세션/OAuth state)
  db/session.py          엔진/세션, init_db(+_ensure_columns 안전망)
  data/region_codes.py   청주 4개 구 코드 + 구 중심좌표(지도)
  models/__init__.py     ORM 전체(아래 데이터 모델)
  sources/
    molit/               국토부 실거래 8종(endpoints/client/normalize)
    applyhome·news·finlife·hf·seomin.py   청약/뉴스/은행/정책/서민금융 커넥터
  pipeline/collect.py    수집(live)·검증(fixtures)·dedup upsert·캐시 무효화
  services/
    stats.py             집계(median 우선·표본부족 null)
    loan.py·costs.py     대출 한도·세금/총비용
    geocode.py·poi.py    좌표·인근 POI
    storage.py           사진 업로드(local/S3)
  api/
    dashboard·home·complex·loan·favorites·personal   시세·대출·개인화
    auth·listings·search·admin·community             로그인·매물·검색·관리자·게시판
  web/index.html         단일 React UI(빌드 없음, DEMO 폴백)
  fixtures/              오프라인 검증 표본(is_sample)
frontend/                웹 빌드(Vite) — 정본 src/main.jsx + PWA(manifest·아이콘·SW). npm run build → dist/ (운영 서빙·스토어용; 컷오버 구성 완료)
scripts/                 run_collect·geocode·scheduler·db_upgrade·verify_region_codes
migrations/              Alembic(env.py가 앱 설정 URL 사용, 0001→0002 baseline)
skills/                  모듈별 상세 개발지침(Claude Code가 먼저 읽음)
run.py                   원클릭 실행      docker-compose.yml  로컬 PostgreSQL(선택)
CLAUDE.md                Claude Code 작업 규칙·검증 루틴    ROADMAP.md  진행현황 SSOT
```

### 데이터 모델(요약)
`Region` · `Complex` · `Transaction`(dedup_key 유니크·원본보존) · `Favorite` · `UserPref` · `RecentView` · `SavedSearch` · `Account` · `DeviceLink` · `Listing`(매물) · `Inquiry`(문의·리드) · `Subscription`(구독) · `Post` · `Comment`(parent_id 대댓글) · `PostLike` · `ReportLog` · `Notification` · `Bookmark`. 조회·중복 방지를 위한 인덱스/유니크 제약을 부여했습니다.

---

## 대규모 운영을 위한 구조 점검 & 개선

실제 유료 서비스를 가정해 구조를 점검하고, 사용자 증가 시 먼저 병목이 되는 항목부터 개선 중입니다(인프라가 아닌 코드·데이터 구조 관점).

| # | 항목 | 상태 |
|---|---|---|
| ③ | 동시성 카운터(조회·좋아요·댓글·신고) 원자적 `UPDATE`로 교체 — lost update/경합 제거 | ✅ 완료 |
| ② | 시세 집계 캐시(데이터 버전 기반) — 매 요청 전체 스캔+Python median 제거 | ✅ 완료 |
| ⑤ | 마이그레이션 일원화 — Alembic 베이스라인 + `db_upgrade` | ✅ 완료 |
| ⑥ | 실거래 정정·해제 반영(현재는 신규만 적재 → stale 가능) | ⏳ 예정 |
| ④ | 검색 인덱스(선두 와일드카드 LIKE) | ✅ pg_trgm GIN(0016·PostgreSQL), SQLite는 스캔 폴백 |
| ① | 프런트 빌드(Babel 제거) — `frontend/` Vite **정본** + PWA(오프라인·앱셸·업데이트배너) | ✅ 구성 완료(컷오버 멀티스테이지). 운영 빌드 검증만 남음 |

자세한 진행현황·다음 작업은 [`ROADMAP.md`](./ROADMAP.md)가 단일 출처(SSOT)입니다.
모바일 앱(스토어) 출시·장기운영 경로는 [`MOBILE_APP_STRATEGY.md`](./MOBILE_APP_STRATEGY.md)(웹 → Vite → Capacitor) 참조.
프로덕션 배포·운영(Dockerfile·compose·CORS·HTTPS·배포 전 점검)은 [`DEPLOY.md`](./DEPLOY.md) 참조.
수익화 전략(기능 중심·단계 로드맵·객관성 가드레일)은 [`MONETIZATION.md`](./MONETIZATION.md) 참조.
출시→매출 단계 전략(GTM·운영자 체크리스트·KPI)은 [`LAUNCH.md`](./LAUNCH.md) 참조.
계층별 테스트 방법은 [`TESTING.md`](./TESTING.md), 스토어 등록 메타·개인정보 라벨 템플릿은 [`store/`](./store) 참조.

---

## 면책

- 실거래가는 신고 지연·정정·해제가 있어 **참고용**이며 법적 효력이 없습니다(출처: 국토교통부).
- 대출·세금 결과는 공시정보 기반 **추정치**이며 실제 승인·금리·한도는 개인 심사로 달라집니다. 본 서비스는 금융/세무 자문업이 아닙니다.
- 커뮤니티 글은 사용자 의견으로 공식 정보가 아닙니다.
- 각 공공데이터의 출처 표기 의무와 지도/POI SDK 약관을 준수합니다.

## 데이터 구조 설명서
운영자용 데이터 저장 구조·컬럼·흐름·집계 기간·PostgreSQL 확인 방법은 **[DATA.md](./DATA.md)** 참조.
