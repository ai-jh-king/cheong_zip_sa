# 데이터 구조 설명서 (운영자용)

> 청주 부동산 플랫폼의 **데이터가 어떻게 저장되고, 각 테이블·컬럼이 무엇을 뜻하며, 어떤 흐름으로 들어오고 집계되는지**를 정리한 문서입니다. 코드를 몰라도 운영자가 데이터를 이해·점검할 수 있도록 작성했습니다. (스키마의 권위 소스는 `app/models/__init__.py` + `migrations/` 입니다.)

---

## 0. 한눈에

- **DB**: 운영은 **PostgreSQL**, 로컬 개발은 SQLite. 스키마는 동일.
- **핵심 데이터**: `transactions`(실거래) · `complexes`(단지) · `regions`(지역). 나머지는 매물(UGC)·커뮤니티·개인화·운영용.
- **금액 단위는 모두 만원** (예: `deal_amount = 50000` → 5억).
- **원본·출처를 항상 보존**(`source`, `raw_payload`) → "왜곡 없음" 원칙.
- 모의/예시 데이터는 `is_sample=true`, 해제(취소)된 거래는 `is_canceled=true`로 **표시만 하고 집계에서 제외**(삭제하지 않음).
- 개인 식별정보는 저장하지 않음(로그인 전엔 익명 `device_id`, 대출 민감정보는 미저장).

---

## 1. 저장 환경

| 항목 | 운영(Production) | 개발(Local) |
|---|---|---|
| DBMS | PostgreSQL 13+ | SQLite(파일) |
| 스키마 생성 | **Alembic** (`db_upgrade upgrade head`) | `create_all`(자동) |
| 접속 설정 | `.env`의 `DATABASE_URL` | 미설정 시 `cheongju_local.db` |
| 인코딩 | UTF-8 | UTF-8 |

> 운영(PG)에서는 `run.py`가 `create_all`을 호출하지 않습니다. 스키마는 **오직 Alembic 마이그레이션**으로 관리됩니다(드리프트 방지).

---

## 2. 공통 규칙 (반드시 이해)
- **스키마 관리**: 운영(PostgreSQL)=Alembic 마이그레이션이 권위. 개발/폴백(SQLite)=앱 시작 시 `_ensure_columns`가 **모델(Base.metadata)에서 컬럼을 자동 도출**해 누락분을 ALTER ADD(재발 방지). 신규 컬럼은 모델에 추가하면 SQLite 자동 반영 + 운영은 마이그레이션 파일 필요.

이 4가지는 거의 모든 테이블에 공통으로 적용되는 "왜곡 없음" 장치입니다.

- **`source`** (transactions): 데이터 출처. 예) `MOLIT_APT_TRADE`(국토부 아파트 매매), `FIXTURE`(테스트). 어디서 온 데이터인지 추적용.
- **`raw_payload`** (JSON): API **원본 응답을 그대로 보존**. 정규화 과정에서 값이 의심되면 원본과 대조 가능.
- **`is_sample`** (boolean): **모의/예시 데이터** 표식. 실데이터가 없을 때 화면 예시로만 쓰며, 화면엔 "예시" 배지가 붙습니다. 집계 신뢰도 판단에 사용.
- **`is_canceled`** (boolean): 신고가 **해제(취소)**된 거래. **삭제하지 않고** 표시만 하며 **모든 시세 집계에서 제외**합니다.
- **금액 단위**: `deal_amount`/`deposit`/`monthly_rent`/`price_official` 등 **모두 만원**.
- **익명성**: 로그인 전 사용자는 개인정보 없이 **`device_id`(기기 임의 식별자)**로만 구분합니다.

---

## 3. 핵심 데이터 테이블

### 3.1 `regions` — 지역(법정동 5자리)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `lawd_cd` (PK) | VARCHAR(5) | 법정동 코드 앞 5자리. 청주 4개 구: 상당 `43111`, 서원 `43112`, 흥덕 `43113`, 청원 `43114` |
| `sido` | VARCHAR(20) | 시·도(기본 "충청북도") |
| `sigungu` | VARCHAR(40) | "청주시 OO구" |
| `dong` | VARCHAR(40), null | 동(선택) |
| `lat`,`lng` | FLOAT, null | 좌표(지오코딩) |

### 3.2 `complexes` — 단지/건물

단지(아파트·오피스텔) 단위 정보. 비아파트는 단지 개념이 약해 null이 많습니다. 보강 정보(K-apt·공시가격)는 **없으면 null**(추정값을 채우지 않음).

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` (PK) | INTEGER | 단지 ID |
| `name` | VARCHAR(120) | 단지명 |
| `lawd_cd` (FK) | VARCHAR(5) | 소속 지역 |
| `property_type` | VARCHAR(20) | apartment/officetel/rowhouse/detached |
| `build_year` | INTEGER, null | 준공연도 |
| `households` | INTEGER, null | 세대수 |
| `kapt_code` | VARCHAR(20), null | K-apt 단지코드(보강) |
| `dong_count` | INTEGER, null | 동수 |
| `heating` | VARCHAR(40), null | 난방방식 |
| `total_area` | FLOAT, null | 연면적(㎡) |
| `builder` | VARCHAR(120), null | 시공사 |
| `approval_date` | VARCHAR(20), null | 사용승인일 |
| `parking` | INTEGER, null | 총주차대수 |
| `price_official` | INTEGER, null | 공동주택 **공시가격**(만원, 단지·면적 중앙값) |
| `price_basis_date` | VARCHAR(20), null | 공시 기준일 |
| `meta_source` | VARCHAR(40), null | 보강 출처(예 `KAPT`) |
| `enriched_at` | TIMESTAMP, null | 보강 시각 |
| `lat`,`lng` | FLOAT, null | 좌표 |

### 3.3 `transactions` — 실거래 (가장 중요)

정규화된 실거래 1건. 아파트/오피스텔/빌라/단독 + 매매/전세/월세를 **하나의 공통 스키마**로 흡수합니다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` (PK) | INTEGER | |
| `lawd_cd` (FK) | VARCHAR(5) | 지역 |
| `complex_id` | INTEGER, null | 단지 연결(선택) |
| `property_type` | VARCHAR(20) | apartment/officetel/rowhouse/detached |
| `deal_type` | VARCHAR(10) | **trade(매매)/jeonse(전세)/wolse(월세)** |
| `complex_name` | VARCHAR(120), null | 단지명(원문) |
| `dong_name` | VARCHAR(40), null | 법정동명 |
| `exclusive_area` | FLOAT, null | 전용면적(㎡) |
| `floor` | INTEGER, null | 층 |
| `build_year` | INTEGER, null | 준공연도 |
| `contract_date` | DATE, null | 계약일 |
| `deal_amount` | INTEGER, null | **매매가(만원)** — 매매 거래 |
| `deposit` | INTEGER, null | **보증금(만원)** — 전세/월세 |
| `monthly_rent` | INTEGER, null | **월세(만원)** — 월세 |
| `source` | VARCHAR(40) | 출처(예 `MOLIT_APT_TRADE`) |
| `is_sample` | BOOLEAN | 모의데이터 표식 |
| `dedup_key` (UNIQUE) | VARCHAR(200) | **중복 적재 방지 키(금액 포함)** |
| `identity_key` | VARCHAR(220), null, idx | **계약 식별 키(금액 제외)** → 정정/해제 매칭용 |
| `is_canceled` | BOOLEAN, idx | **해제(취소)분 — 집계 제외** |
| `canceled_date` | DATE, null | 해제사유 발생일 |
| `corrected_at` | TIMESTAMP, null | 정정으로 금액이 갱신된 시각 |
| `trade_method` | VARCHAR(12), null | 거래유형: `agent`(중개)·`direct`(직거래)·`null`(미상/전월세 미제공). 직거래는 가족 등 특수관계가 섞일 수 있어 **신뢰 필터**에서 ‘직거래’ 배지로 표시 |

> **실거래 신뢰 필터(운영 메모)**: 시세 왜곡을 줄이기 위해 단지 상세에서 다음을 구분 표시한다. ①해제(`is_canceled`)는 집계 제외 + ‘해제 N건 제외’ 안내, ②정정(`corrected_at`)·③직거래(`trade_method='direct'`)는 거래행에 배지, ④이상치는 **저장값이 아니라** 같은 평형 중앙 평단가 대비 ±30% 초과를 통계층(`stats._tx_out`)에서 계산해 표시(취소선). 표본 신뢰도(`reliability`: low/fair/ok)도 거래건수로 산출. 정책 변경 시 임계값(±30%, 건수 구간)은 `stats._reliability`/`_tx_out`에서 조정.
| `raw_payload` | JSON, null | API 원본 보존 |
| `collected_at` | TIMESTAMP | 적재 시각 |

#### 핵심 개념: `dedup_key` vs `identity_key` (정정·해제 처리)

- **`dedup_key`**(금액 **포함**): 같은 계약·같은 금액이면 동일 → **중복 적재를 막음**.
- **`identity_key`**(금액 **제외**): 같은 계약을 금액과 무관하게 식별 → **정정·해제**를 잡아냄.
- 수집 시 동작:
  - **신규**: identity가 없으면 INSERT.
  - **정정**: 같은 identity가 1건 있고 **금액만 다르면** → 기존 행의 금액을 갱신하고 `corrected_at` 기록(중복 생성 안 함).
  - **해제**: 원본이 해제로 표시되면 → 해당 identity의 활성 행을 `is_canceled=true`로 표시.
- **모든 시세 집계는 `is_canceled=false`인 행만** 사용합니다.

> 인덱스: `(lawd_cd, contract_date)`, `(property_type, deal_type)`, `(property_type, is_canceled)`, `identity_key`. 그리고 PostgreSQL에선 검색 가속용 **pg_trgm GIN 인덱스**(단지명·동명, 마이그레이션 0007).

---

## 4. 그 외 테이블 (요약)

### 매물(UGC) · 커뮤니티
- **`posts.resident`**(bool, 0019): 작성 시점에 서버가 작성자 prefs.my_home과 @단지 태그를 대조한 결과. 자가 신고 불가(클라이언트 값 안 받음).
- **`listings`** — 사용자/중개업자가 올린 **등록 매물**. 실거래(`transactions`)와 **분리**(왜곡 방지). 「중개대상물 표시·광고」 고시 명시항목(면적·층·방향·가격·관리비·중개업체 정보 등)을 컬럼으로 담음. `status`(active/traded/hidden).
- **`inquiries`** — 매물 **문의(리드)**. 사용자가 매물에 남긴 `contact`(연락처·민감)·`message`. **매물 등록자(소유자)만 열람**(`owner_account_id`/`owner_device_id` 비정규화). `consent=True` 필수, `status`(new/read/contacted/closed). 마케팅·제3자 제공 금지. 중개사 대시보드의 "받은 문의"로 노출. (※ 연락처 수집 → 개인정보처리방침에 항목 반영 필요)
- **회원 탈퇴(DELETE /auth/account)**: 계정+기기연결+개인화(favorites/recent_views/saved_searches/user_prefs)+post_likes/bookmarks/report_logs+notifications/push_subscriptions+내 listings+inquiries(받은+보낸)를 **삭제**, posts/comments는 **익명화**(작성자 식별 제거·스레드 보존), subscriptions/consents는 **법정·증빙 보존**. 원자적(한 트랜잭션).
- **`subscriptions`** — 유료 **구독(결제)**. `plan`·`status`(active/canceled/expired)·`provider`(mock/toss/portone)·`expires_at`. **`feature_billing` OFF가 기본**이라 테이블이 있어도 권한 게이팅 비활성(현재와 동일). 권한은 `entitlement.is_premium`(플래그 ON + active 구독).
- **`posts`** / **`comments`** — 커뮤니티 글·댓글(대댓글 1단계). **사용자 작성=개인 의견**(공식정보 아님). `category`(free/qa/info/deal/local), `views/like_count/comment_count/report_count`, `status`(active/hidden).
- **`post_likes`** / **`bookmarks`** — 좋아요·스크랩(중복 방지 UNIQUE). `owner`= `device_id` 또는 `acct:<id>`.
- **`report_logs`** — 신고(중복 방지). 임계치 도달 시 자동 숨김.
- **`notifications`** — 알림(댓글/답글/실거래). 수신자 `account_id`, `is_read`.

### 개인화(익명 기기 기준)
- **`favorites`** — 관심 단지/지역. `device_id` + `target_type`(complex/region) + `target_id`.
- **`recent_views`** — 최근 본 단지(기기당 상한).
- **`saved_searches`** — 저장된 시세 검색 필터(JSON).
- **`user_prefs`** — 기기별 설정(단위·내 동네 등, JSON 1행). **`data.my_home`에 우리집(단지명·lawd_cd·유형) 저장** → 로그인 시 기기 병합으로 동기화(비로그인은 프런트 localStorage).

### 청주 특화(하이퍼로컬)
- **`landmarks`** — 개발 호재. `category`(industry/transport/commercial/residential/public)·`status`(confirmed/ongoing/planned)·`lat/lng`·`summary`·`expected_year`·`source_name/url`·`sort_order`·`is_active`. 시드=`scripts/seed_landmarks`. 출처 필수·집값 단정 금지. (홈 카드·지도 핀·단지상세)
- **`places`** — 생활·교육·운동 시설. `category`(education/sports/living)·`subcategory`(academy_*/daycare/hospital/library/sports 등)·`lat/lng`·`source`. 시드=`scripts/collect_places`(NEIS·data.go.kr)+geocode. 육아환경·초품아·지도 POI의 원천. **미적재면 관련 UI 숨김**.
- **`commute_destinations`/`commute_times`** — 통근 거점·소요시간. 직주근접(단지→거점 직선거리, `commute.hub_access`)에 좌표 재사용. 시드=`scripts/seed_commute`(SK하이닉스 청주캠퍼스 포함).

### 계정 · 운영
- **`accounts`** — 소셜 로그인 계정. `provider`(kakao/naver)+`provider_uid`(UNIQUE), `role`(user/agent), `nickname`.
- **`device_links`** — 기기↔계정 연결(로그인 시 익명 데이터 승격).
- **`consents`** — **개인정보 처리 동의 이력**(대출 민감정보 등). `owner`,`kind`,`policy_version`,`agreed_at` (개인정보보호법 대응).
- **`app_meta`** — 키-값 운영 상태(수집 워터마크·알림 커서·마지막 보강/공시 시각 등).

> 개인화·커뮤니티 테이블의 `is_sample`도 동일하게 "예시" 표식입니다.

---

## 5. 데이터 흐름 (수집 → 정규화 → 적재 → 집계)

```
[국토부 실거래가 API]                (유형별 엔드포인트: 아파트/오피스텔/빌라/단독 × 매매/전월세)
        │  scripts.run_collect / scheduler (일/월 증분)
        ▼
[수집]  최근 N개월(기본 12) × 청주 4개 구 조회
        ▼
[정규화] 유형별 응답 → 공통 transactions 스키마로 매핑 + dedup_key/identity_key 생성
        ▼
[적재]  upsert: 신규=INSERT · 정정=금액 갱신 · 해제=is_canceled 표시 (raw_payload 보존)
        ▼
[집계]  services/stats.py — is_canceled=false 만으로 중앙값·평단가·전세가율·등락·거래량 계산
        ▼
[API/화면] /search, /complex, /dashboard ... (만원 단위, 출처·기준일 표기)
```

- **보강**: `scripts/enrich.py`(K-apt 단지정보), `scripts/import_gongsi.py`(공시가격 CSV) → `complexes` 채움. 없으면 null.
- **외부 API는 매 요청마다 직접 호출하지 않고 자체 DB(`transactions`)에 캐싱**합니다.

---

## 6. 집계 기간 기준 (중요)

- **수집 범위**: 매 수집 시 최근 **12개월**(`.env`의 `collect_months_back`). 오래된 데이터는 **삭제하지 않고** 누적 보관.
- **집계 기본 윈도우 = 최근 12개월** (`.env`의 `aggregate_months`, 기본 12). '현재 시세'로 쓰이는 **중앙값·평단가·전세가율·거래량·예산매칭·랭킹·지도**는 모두 **최근 12개월 실거래만** 사용합니다. → 화면에도 "최근 12개월 실거래 기준" 표기.
  - 구현: `stats._load`(최근 N개월) vs `stats._load_all`(전체 이력).
- **예외(전체 이력 사용)**: ① **전월/전년 대비 등락**(전년=12개월 전 같은 달이라 1년 이상 필요) ② **단지 상세 추이 차트**(1/3/5년 토글). 이 둘만 `_load_all`.
- **단지 상세 '고점/저점 대비'**: 최근 12개월 내 고점/저점 기준(화면 라벨도 "최근 12개월 고점").
- **거래량/급등락 랭킹**: 윈도우 내 최신월 vs 직전월.

> 윈도우 개월 수를 바꾸려면 `.env`에 `AGGREGATE_MONTHS=24` 처럼 설정(화면 표기도 자동으로 따라감).

---

## 7. 보존·파기

- 실거래/단지/집계: **영속 보관**(공개 공공데이터, 개인정보 아님).
- 해제·정정: 삭제하지 않고 표식(`is_canceled`/`corrected_at`)으로 이력 유지.
- 대출 민감정보(소득·신용): **저장하지 않음(stateless)** — 세션 내 계산 후 폐기. 저장 옵션은 사용자 기기에만.
- 동의 이력(`consents`): 보관(법적 증빙).

---

## 8. 개인정보

- 로그인 전: 개인정보 없음, **익명 `device_id`만**.
- 로그인: `accounts`(provider uid·닉네임)만. 주민번호·계좌 등 **수집 안 함**.
- 대출 추천: 소득·신용 **미저장**(동의 이력만 `consents`에 기록).
- 운영 시 `JWT_SECRET`/`ADMIN_TOKEN` 설정, 처리방침 게시 필요(OPERATIONS.md 참조).

---

## 9. PostgreSQL 데이터 확인 방법

### 9.1 psql로 접속
```bash
# Windows: 시작메뉴 "SQL Shell (psql)" 또는
psql -U cheongju -d cheongju -h localhost
# 비밀번호 입력
```

### 9.2 테이블·구조 확인
```sql
\dt                          -- 전체 테이블 목록
\d transactions              -- transactions 컬럼·타입·인덱스 상세
\d+ complexes                -- 더 자세히(설명 포함)
\di                          -- 인덱스 목록
\l                           -- 데이터베이스 목록(인코딩 확인)
```

### 9.3 데이터 양·내용 확인
```sql
-- 적재된 실거래 건수(해제 제외)
SELECT count(*) FROM transactions WHERE is_canceled = false;

-- 구별·거래유형별 건수
SELECT lawd_cd, deal_type, count(*)
FROM transactions WHERE is_canceled = false
GROUP BY lawd_cd, deal_type ORDER BY lawd_cd, deal_type;

-- 최근 매매 실거래 10건
SELECT contract_date, complex_name, exclusive_area, floor, deal_amount
FROM transactions
WHERE deal_type = 'trade' AND is_canceled = false
ORDER BY contract_date DESC LIMIT 10;

-- 데이터 신선도(가장 최근 계약일)
SELECT max(contract_date) FROM transactions WHERE is_canceled = false;

-- 해제·정정 건수
SELECT
  count(*) FILTER (WHERE is_canceled) AS canceled,
  count(*) FILTER (WHERE corrected_at IS NOT NULL) AS corrected
FROM transactions;

-- 모의데이터가 섞여 있는지(운영에선 0 이어야 정상)
SELECT count(*) FROM transactions WHERE is_sample = true;

-- 단지 보강(공시가격) 채워진 단지 수
SELECT count(*) FROM complexes WHERE price_official IS NOT NULL;

-- 운영 메타(마지막 수집/보강 시각 등)
SELECT * FROM app_meta;
```

### 9.4 pgAdmin(GUI)로 보기
1. pgAdmin 실행 → 서버 등록(host `localhost`, port `5432`, user `cheongju`).
2. 좌측 트리: `Databases > cheongju > Schemas > public > Tables`.
3. 테이블 우클릭 → **View/Edit Data > All Rows**로 내용 확인.
4. 상단 쿼리툴(Query Tool)에 위 SQL을 붙여 실행.

### 9.5 앱으로 빠르게 점검 (DB 접속 없이)
- `http://localhost:8000/health` → `db_ok`, `data_version`, 키 설정 여부.
- `http://localhost:8000/status/data` → 구별 건수·최신 계약일·해제/정정 수·신선도(stale) 한눈에.

---

## 부록. 빠른 점검 체크리스트
- [ ] `\dt`에 18개 테이블이 보이는가
- [ ] `transactions` 건수 > 0 (실데이터 적재 확인)
- [ ] `is_sample=true` 건수 = 0 (운영에서 모의 미혼입)
- [ ] `max(contract_date)`가 최근인가 (수집 스케줄러 정상)
- [ ] `/status/data`가 stale이 아닌가

---

## 통근권 (commute_destinations / commute_times)

청주 특화 차별 기능 ②. "직장/목적지까지 N분 이내 단지"를 찾기 위한 데이터.

### `commute_destinations` — 목적지(운영자 관리)
| 컬럼 | 설명 |
|---|---|
| `key` | 안정 슬러그(예: `osong_ktx`). 코드/시드 참조용, unique |
| `name` / `category` | 표시명 / 분류(transit·job·public·education·medical) |
| `lat` / `lng` | 좌표. **실제 좌표만** 사용(없으면 검색 제외) |
| `address` | 주소(지오코딩 재계산용) |
| `coord_method` | `seed_approx`(시드 근사) / `geocoded`(주소 지오코딩) / `manual` |
| `is_active` / `sort_order` | 노출 여부 / 정렬 |

> 운영: 목적지는 **코드 수정 없이** 추가/비활성. `python -m scripts.seed_commute` 로 시드 upsert, `--geocode` 로 주소 기반 좌표 정밀화(카카오 키 필요, coord_method→geocoded 승격).

### `commute_times` — (단지×목적지×수단) 통근시간 캐시
| 컬럼 | 설명 |
|---|---|
| `complex_id` / `destination_id` / `mode` | 복합 유니크(`uq_commute`). mode=car/transit/walk |
| `minutes` / `distance_m` | 소요시간(분) / 거리(m) |
| `method` | **`api`**(카카오 길찾기 실측) / **`haversine`**(직선거리 추정) — 정확도 라벨(왜곡 없음) |
| `source` / `computed_at` | 출처 / 계산시각(신선도, `commute_cache_ttl_days`) |

> 운영: `python -m scripts.compute_commute [--mode transit] [--force]` 로 배치 사전계산(증분, 단지 좌표 선행 필요 → `scripts.geocode`). `car`+카카오 키면 실측(`api`), 아니면 추정(`haversine`). 캐시가 비어도 `/commute/search`는 즉석 haversine 추정으로 동작하고, 배치 후 실측으로 자동 대체.
> 추정 파라미터(`commute_avg_kmh_*`, `commute_detour_factor`)는 설정값 — 보정 시 .env/config에서만 변경.
