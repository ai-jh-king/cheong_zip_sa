# 데이터 수집·정규화·커넥터 (skills)

## 실거래 파이프라인 (M1)
- 소스: 국토부 실거래가 8종(아파트/오피스텔/빌라/단독 × 매매/전월세) — `sources/molit/`.
- 키: `MOLIT_SERVICE_KEY`(= data.go.kr 디코딩 키). **data.go.kr는 계정 키 1개를 모든 활용신청 데이터에 공통 사용** → 청약홈·HF·서민금융도 같은 키.
- 지역코드: 실거래 API는 **법정동 앞 5자리**. 청주 상당 43111 / 서원 43112 / 흥덕 43113 / 청원 43114. `scripts/verify_region_codes.py`로 검증.
- 흐름: 배치 수집(증분) → `normalize_row`로 정규화 → DB 캐싱. **매 요청마다 외부 API 직접 호출 금지**(캐싱 필수).

## 정규화 규칙 (`sources/molit/normalize.py`)
- 유형별 응답 필드가 다름 → `FIELD_CANDIDATES`로 관용적 매핑(여러 후보 키 시도).
- 못 찾은 필드는 `None`(절대 추측/0으로 채우지 않음).
- 거래금액·보증금은 콤마 제거 후 int(만원). 전용면적 float(㎡). 평단가는 `만원/평 = 금액 ÷ (면적/3.305785)`.
- `raw_payload`에 원본 보존, `source`·`is_sample` 기록.
- `dedup_key`로 중복 제거.

## 새 외부 커넥터 추가 패턴 (청약/뉴스/finlife/HF/POI 공통)
모든 커넥터는 아래 **방어적 패턴**을 따른다:
```python
def fetch_xxx(...):
    s = get_settings()
    key = s.<related_key> or s.molit_service_key   # data.go.kr 계열이면 MOLIT 재사용
    if not key (or not url): return None           # 키/URL 없으면 None
    try:
        r = httpx.get(URL, params={...}, timeout=12)
        if r.status_code != 200: log; return None
        rows = tolerant_extract(r.json())          # 응답 구조 다양성 흡수
        return normalize(rows) or None
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log; return None
```
- **반환 None → 상위(API/서비스)가 예시(sample)로 폴백** → 앱이 안 깨진다.
- 응답 필드명은 **추측 금지**. 모르면 tolerant 후보 매핑 + "⚠️ Swagger 확인" 주석.
- 저작권: 뉴스는 제목·짧은 요약·링크만(원문 전재 금지).

## 현재 커넥터 상태
| 파일 | 소스 | 키 | 비고 |
|---|---|---|---|
| sources/molit | 국토부 실거래 8종 | MOLIT | 핵심·연동완료 |
| sources/applyhome | 청약홈 분양정보 + **경쟁률/가점/주택형별**(`APPLYHOME_COMPETITION_URL`) | MOLIT 재사용 | 청주/충북 필터, 공고↔주택형 병합 |
| sources/news | 네이버 뉴스 | NAVER_SEARCH | 제목+요약+링크 |
| sources/finlife | 금감원 은행 **주담대+전세** | FINLIFE | baseList+optionList 조인, 금리순 |
| sources/hf | HF 디딤돌·보금자리 | MOLIT 재사용 | `HF_POLICY_API_URL` 설정 시 켜짐 |
| sources/seomin | 서민금융 '한눈에' | MOLIT 재사용 | `SEOMIN_API_URL` 설정 시 켜짐 |
| services/geocode | **네이버 지오코딩(우선)** + 카카오 폴백 | NAVER_MAP(재사용)/KAKAO_REST | 단지·주소→좌표 캐싱 |
| services/poi | 카카오 카테고리(네이버 동등 API 없음) | KAKAO_REST | 인근 학교/지하철/마트/병원/중개업소(AG2) |

## 지역/유형 확장
- 새 구/시: `data/region_codes.py`에 코드 추가 → 집계·UI 자동 반영(하드코딩 없음 유지).
- 새 매물유형: 유형별 엔드포인트·정규화 매핑만 추가.


## 외부 호출 캐싱 (app/core/cache.py)
대출·뉴스·청약 등 **외부 API 응답은 인프로세스 TTL 캐시**로 감싼다(매 요청 외부호출 금지).
- 데코레이터 `@ttl_cached("cache_ttl_*_sec", 기본초)` 를 fetch_* 함수에 부착.
- TTL: 대출 6h / 청약 30m / 뉴스 10m (config 로 조정).
- single-flight(동시요청 1회만 호출) + negative caching(None 은 짧게).
- 새 외부 커넥터를 추가하면 **반드시 같은 데코레이터로 캐싱**할 것.
- 확장: 서버 다중화 시 Redis 로 교체(get_or_set 인터페이스 유지). DB 파생 응답(board 등)도 필요 시 동일 캐시 적용 가능.

## 등록 매물(UGC)은 실거래와 분리
- `Listing`(=`/listings`)은 사용자/중개업자 등록 매물. **실거래(Transaction)와 절대 합산·혼동 금지**(응답 source="listing").
- 표시·광고 명시사항(국토부 고시) 컬럼 보유. agent 등록은 사무소 명시사항 필수 검증.
- UI는 '등록매물'·'예시' 배지로 구분, 허위매물 고지 노출.


## 실거래 해제(취소)·정정 반영
국토부 응답은 행마다 해제여부(cdealType='O')·해제사유발생일(cdealDay)을 제공한다.
- 정규화: is_canceled/canceled_date 파싱, identity_key(금액 제외 계약식별) 생성.
- 적재(upsert v2):
  - 해제행 → 같은 identity_key 활성 거래를 is_canceled=True 로 표시(집계 제외).
  - 정정행(같은 identity_key·다른 금액 1건) → 기존 행 금액을 '갱신'(중복 생성 금지).
  - 완전 동일(dedup_key) → skip(멱등). 활성 0건 → 신규.
- 집계/검색: is_canceled.isnot(True) 로 해제분 제외(기존 NULL 행도 활성으로 안전 처리).
- 기존 데이터: 수집 시작 시 backfill_identity_keys 로 identity_key 채움(정정/해제 매칭 활성화).
- 스키마: Transaction.identity_key/is_canceled/canceled_date/corrected_at. 마이그레이션 0003_tx_cancel.


## 단지 기본정보(공동주택관리정보 K-apt)
- data.go.kr 공통키(MOLIT_SERVICE_KEY). 흐름: 시군구 단지목록→kaptCode→기본정보(getAphusBassInfoV3).
- 주요 필드: kaptdaCnt(세대수) kaptDongCnt(동수) kaptUsedate(사용승인일) codeHeatNm(난방) kaptTarea(연면적) kaptBcompany(시공사).
- 코드: app/sources/kapt/(client+normalize), app/services/enrich.py. 엔드포인트는 config(KAPT_LIST_URL/KAPT_INFO_URL), Swagger 로 확정.
- 왜곡 방지: 매칭 실패/미설정/누락 → null. 아파트만 대상. 단지 상세는 complex_meta 로 노출(출처 표기).

## 정규화 진단 (NormalizationReport) — 실데이터 매핑 안전장치
- `molit/normalize.py`의 `NormalizationReport`를 `normalize_row(..., report=r)`로 넘기면(선택) 핵심 필드 미매핑을 집계. **넘기지 않으면 동작 완전 동일(기존 영향 없음).**
- 핵심 필드: deal_amount(매매), contract_date(항상), exclusive_area(아파트/오피/빌라), complex_name(아파트/오피). 단독·다가구는 단지명/면적 제외(오탐 방지). 전월세는 deal_amount 제외.
- collect_live 가 수집 중 report 를 누적 → 반환 `mapping`(rows·misses·원본 키 샘플) + last_collect.mapping_misses + 미매핑 시 단일 WARNING 로그. JobRun.stats 로 `/admin/runs`에서 확인.
- `scripts/doctor.py`는 실데이터 표본을 정규화해 **"정규화 필드 매핑"** 항목으로 즉시 진단(미매핑 시 ❌ + FIELD_CANDIDATES 보강 안내). 실데이터 배포 시 1순위 리스크(필드 불일치로 데이터가 조용히 비는 것)를 시끄럽게 만든다.
- 보강법: 미매핑으로 뜬 필드의 원본 키 샘플을 보고 `FIELD_CANDIDATES`에 후보만 추가(임의 단정 금지).
