# 생활·교육·운동 시설 데이터 출처 (Place) — 명세 & 수집 청사진

> 통합 모델 `Place`(model)에 아래 공공데이터를 normalize해 적재한다. **모든 값은 공식 공공데이터**(왜곡 없음).
> 좌표 없는 행은 거리/지도 제외. 분류는 `app/services/places.classify_academy()` 키워드 매핑.
> ⚠️ 각 API의 **정확한 필드명·엔드포인트·페이지네이션은 활용신청 후 Swagger로 확정**(추측 금지). 아래는 확정용 체크리스트.

## 공통
- 공공데이터포털(data.go.kr) 회원가입 → 활용신청 → serviceKey 발급(승인 1~24h). 무료.
- 출처표기 의무: 화면에 "자료: <기관/데이터셋>" 표기.
- 청주 한정: 시군구 코드/주소로 충북 청주(상당 43111·서원 43112·흥덕 43113·청원 43114)만 적재.
- 적재 시 `source="public"`, `source_dataset`, `source_key`(원천 고유키, 중복방지), 좌표는 WGS84로 통일.

## 분야별 데이터셋

### 교육 (education)
| 세분류 | 데이터셋 | 핵심 필드 | 좌표 | 갱신 |
|---|---|---|---|---|
| academy_* (학원·교습소) | **전국학원및교습소표준데이터**(data.go.kr 15096277) | 학원명·분야·교습계열·교습과정·정원·등록상태·수강료(공개분)·주소 | 주소 → 지오코딩 필요(좌표 미포함 가능) | 수시 |
| (초중고 배정 참고) | 전국초중등학교기본정보표준데이터(15107734) | 학교명·소재지·남녀공학·주소 | 확인 필요 | 월 |

- **분류**: 분야/교습계열/교습과정 텍스트 → `classify_academy()` → academy_lang/pe/art/it/exam/etc.
- **수강료**: 공개분만 `tuition`. 비공개는 null(왜곡 방지).

### 운동·체육 (sports)
| 세분류 | 데이터셋 | 핵심 필드 | 좌표 | 갱신 |
|---|---|---|---|---|
| sports (체육시설) | **전국체육시설 정보**(국민체육진흥공단) / **전국공공시설개방정보표준데이터**(15013117) | 시설명·유형(체육관/수영장/풋살 등)·주소·**사용료**·수용인원·면적 | **위도·경도 포함**(개방정보) | 주간/월 |
| (민간 헬스·필라테스 등) | 향후: 지방행정 인허가(체력단련장업 등) | 사업장명·영업상태·주소·좌표 | 포함 多 | 주간 |

- 공공시설개방정보는 **사용료까지** 있어 `tuition`에 매핑 가능.

### 생활 (living)
| 세분류 | 데이터셋 | 핵심 필드 | 좌표 | 갱신 |
|---|---|---|---|---|
| library (도서관) | **전국도서관표준데이터**(15013109) | 도서관명·유형·운영시간·좌석수·주소 | **위도·경도 포함** | 월 |
| hospital (병원·의원) | **전국의료기관표준데이터**(15096293) | 기관명·종별·주소 | ⚠️ **EPSG:5174(Bessel 중부원점TM)** → WGS84 변환 필요 | — |
| pharmacy (약국) | 전국약국표준데이터 | 약국명·주소·운영시간 | 확인 필요 | 월 |
| daycare (어린이집/유치원) | 어린이집정보·유치원알리미 | 기관명·정원·주소 | 확인 필요 | 월 |

- ⚠️ **의료기관 좌표계 주의**: EPSG:5174 → WGS84 변환(pyproj 등) 후 저장. 변환 전 좌표는 저장 금지(왜곡 방지).

## 수집기 구현 가이드(향후 `app/sources/places_gov.py`)
1. 데이터셋별 fetch 함수: serviceKey + 페이지네이션(numOfRows/pageNo) → 원본 dict 목록.
2. normalize: 필드 → `Place`(name·subcategory·course·road_address·lawd_cd·dong_name·lat·lng·tuition·status·attrs·source_dataset·source_key).
3. 청주 필터(시군구/주소), 좌표 정규화(WGS84), `classify_academy`로 학원 세분류.
4. upsert by `source_key`(중복 방지). 배치(scripts.collect_places)로 주기 적재 + 크론.
5. 좌표 없는 행은 주소 지오코딩(scripts.geocode 재사용) 또는 좌표 null 저장(거리계산 제외).

## 향후 확장(부록 B)
- `source="claimed"`: 업체가 직접 등록·보강(시간표·실수강료·사진). `claimed_by`=업체 계정.
- `source="ad"`: 광고/제휴(표기 의무·객관성 고지). 현재 OFF, 자리만.

## 수집 실행 (v1.114~)
- 키: `.env`에 `ACADEMY_SERVICE_KEY`(없으면 `MOLIT_SERVICE_KEY` 재사용 시도). 데이터셋 활용신청 필요.
- 적재:
  - `python -m scripts.collect_places academy` → 학원·교습소
  - `python -m scripts.collect_places sports` → 체육시설(수영장·풋살 등, 사용료 포함)
  - `python -m scripts.collect_places medical` → 의료기관(병원·의원·약국, ⚠️ EPSG:5174→WGS84 pyproj)
  - `python -m scripts.collect_places library` → 도서관
  - `python -m scripts.collect_places daycare` → 어린이집·유치원
  - `python -m scripts.collect_places all` → 전부(학원·체육·의료·도서관·어린이집)
- 좌표 없는 학원: `python -m scripts.geocode` 로 보강(주소→좌표). 좌표 없으면 거리/지도 제외(목록엔 노출).
- ⚠️ `app/sources/academy.py`의 `ACADEMY_URL`·필드 후보(F)는 **Swagger로 실제 경로/필드 확정** 후 보강. tolerant 매핑이라 흔한 이름은 자동 흡수.

## ✅ API 검증 상태 (실측 확인 — 2026-06)
> "진짜 API 활용 가능한 데이터만" 원칙. 페이지 직접 확인 결과.

| 분야 | 상태 | 실제 API 시스템 | 키 | 좌표 |
|---|---|---|---|---|
| 학원·교습소 | ✅ **확인** | **NEIS** open.neis.go.kr `acaInsTiInfo` (data.go.kr 15096277은 CSV) | NEIS 별도 키 | 없음→geocode |
| 어린이집 | ✅ **확인** | data.go.kr odcloud 15013108 (uddi 확인) | data.go.kr | ✅ 위경도(+놀이터수·CCTV·정원·현원) |
| 체육시설(공공시설개방) | ⚠️ 미검증 | data.go.kr 15013117(표준, 위경도·사용료 항목 확인) — 엔드포인트 활용신청 후 확정 | data.go.kr | ✅ |
| 도서관 | ⚠️ 미검증 | data.go.kr 15013109(표준) | data.go.kr | ✅ |
| 의료기관 | ⚠️ 미검증 | data.go.kr(표준) | data.go.kr | ⚠️ EPSG:5174 |
| 유치원 | ⚠️ 미검증 | data.go.kr 15096279(표준) | data.go.kr | 확인 필요 |
| 도시공원·놀이터 | ⚠️ 미검증 | data.go.kr 15012890(유희시설=놀이터 항목 확인) | data.go.kr | ✅ |
| 실외운동기구 | ⚠️ 미검증 | data.go.kr 15139207 | data.go.kr | ✅ |

- ✅=페이지에서 API 제공·필드 직접 확인. ⚠️ 미검증=데이터셋은 실재하나 **엔드포인트(uddi)·필드는 활용신청 후 본인 API 페이지에서 확정** 필요(코드의 _URL은 추정 placeholder).
- 정정 이력: 학원은 odcloud가 아니라 **NEIS** 제공(코드 정정 완료, source_dataset=neis_academy).
