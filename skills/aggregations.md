# 집계 규칙 (services/stats.py) — skills

## 원칙
- **중앙값(median) 우선**: 평단가·가격대는 평균보다 median(이상치에 강함). 거래량은 count.
- **표본 부족 시 None**: 데이터 없는 칸은 `None`(미보간). 신고가/신저가는 이전 기록(2개월+) 없으면 제외 — 지어내지 않는다.
- `LOW_SAMPLE_THRESHOLD` 미만이면 `low_sample=True`로 표기(UI에서 "표본부족").
- 평단가: `_pyeong_unit(amount, area) = amount / (area/PYEONG)`, PYEONG=3.305785.
- 면적 버킷 `AREA_BUCKETS`: small<60 / medium 60~85 / large 85+ ㎡.

## 주요 함수
- `city_summary`, `by_region` — 구별 평균/전세가율.
- `trend(months)` — 구별 월 평균 시계열(빈 달 None). 홈 다중선그래프용.
- `city_trend(months)` — 전체 월 중앙값.
- `top_trades`, `top_trades_by_ppm` — 매매가/평단가 순위. `area_band`(all/small/medium/large) 필터 지원.
- `active_regions`, `complex_movers` — 거래 활발 구 / 등락 큰 단지.
- `newly_high` / `newly_low` — 신고가/신저가(단지×면적대, 2개월+).
- `gu_price_ranking` — 구별 평단가 중앙값 랭킹 + `month_count`(최근월 거래량).
- `recent_trades(per_gu)` — 구별 최신 윈도(날짜) → **가격순** 정렬 + `is_high`(신고가) 플래그.
- `complex_detail` — 단지 상세: 추이·전고점/전저점·면적/층별 평단가·전세가율(갭)·가격대·거래수.
- `heatmap` — 좌표 있는 단지별 평단가 median(없으면 제외).

## 새 지표 추가 시
1. `_load(db, property_type)`로 거래를 받고, **trade/deal_amount/area null 가드** 후 계산.
2. 표본 부족 → None. 평균보다 median 우선.
3. 엔드포인트(`api/dashboard.py` 등)에서 노출. 가능하면 fixtures로 오프라인 검증.

## 정렬·순서 통일(확장 대비)
- 홈은 **평단가 랭킹 순서**(`gu_order`)를 단일 기준으로, 구별 랭킹·최신거래·추이 범례를 모두 같은 순서로 정렬한다(`api/dashboard.py:board`).
- 새 구별 섹션을 추가하면 동일 `gu_order`로 정렬할 것.

## 가격 분포 (price_distribution)
- 매매=deal_amount·전세=deposit·월세=monthly_rent 기준 가격대별 거래건수 + 중앙값·p25·p75.
- 표본 < 8 → buckets=None(`insufficient`), 수치 None(왜곡 방지). 버킷폭은 데이터 범위로 자동(≤12개). 엔드포인트 `/dashboard/distribution`.
- 프런트(시세 탭)는 동일 로직을 필터된 rows에 적용해 화면 필터와 1:1 일치(커스텀 평형 포함). 백엔드 함수는 API/타뷰 재사용용.

## 대장아파트 (landmark_apts)
- 단지(complex_name+lawd_cd)별 매매가 **중앙값** 상위 N. 최고가 1건이 아니라 중앙값(이상치 방지). 평단가·대표면적·거래수 동봉. `/dashboard/board`의 `landmark`.


## 집계 캐시 (대규모 운영)
- 무거운 집계 함수(첫 인자 `db: Session`)는 `@stat_cached()`(app/core/cache.py)를 붙인다.
  - 캐시 키는 (함수명, **data_version**, 인자)이며 `db`는 제외 → 같은 데이터 버전 안에서 1회만 계산.
  - 반환은 deepcopy(호출부 변형이 캐시를 오염시키지 않음), single-flight(스탬피드 방지), TTL `cache_ttl_stats_sec`(기본 600s) 백스톱.
- 원천 데이터가 바뀌는 경로(`pipeline/collect.py` 적재, `services/geocode.py` 좌표)에서 **`bump_data_version()`**를 호출해 즉시 무효화 → 사용자는 항상 최신 시세를 본다.
- 새 집계 함수를 추가하면: (1) median 우선·표본부족 None 규칙 준수, (2) `@stat_cached()` 부착, (3) 데이터 변경 경로에서 버전 bump 확인.

## 집계 윈도우(최근 N개월)
- `_load`=최근 `aggregate_months`(기본 12)개월, `_load_all`=전체 이력. 현재 시세(중앙값·평단가·전세가율·거래량·랭킹·비교·예산매칭)는 `_load`. 전년대비(city_summary YoY)·단지 다년 추이는 `_load_all`.
- 화면 표기: /config 의 `aggregate_months` → 프런트 `AGG_MONTHS` → '최근 N개월 실거래 기준'.


## 시세 탭 서버 집계 (price_overview) — 확장성
- 시세 탭(지역→단지 드릴다운)은 **서버 집계** `stats.price_overview(db, lawd_cd, property_type, band)` 사용. 과거 클라이언트가 거래 500건을 받아 집계하던 구조를 대체(데이터·지역 확장 시 표본 왜곡·페이로드 폭증 방지).
- 반환: `{gu, property_type, summary:{median,ratio(전세가율),count,dM(전월등락%)}, complexes:[{name,lawd_cd,gu,dong,property_type,median,count,last_date,contains_sample_data}]}`. 윈도우=`_load`(최근 N개월), 해제 제외, 표본 포함하되 배지. band: all|small(<60㎡)|medium(60~85)|large(≥85). `@stat_cached()`.
- API `GET /price/overview?lawd_cd=&property_type=&band=`(property_type 전체/all→"all"). 프런트는 이 응답을 받아 검색(q)·정렬만 클라이언트 처리. 데모(오프라인)에선 `demoOverview()` 폴백(동일 형상).

## 생활권 점수 (living) — services/living.py
- 단지 상세의 인프라 접근성 점수. 입력=`poi.nearby` 결과(반경 1.5km 카테고리별 장소+거리). **임의 장소 생성 금지**(왜곡 없음).
- 규칙(공개): 카테고리별 '가장 가까운 시설 거리' 기반 — 300m 이내 100점, 1.5km 40점(선형), 반경 내 없음 0점. 카테고리·가중치 `CATEGORIES`(교통0.30·편의0.25·학교0.25·의료0.20) 가중평균=종합(0~100)+등급(최상/좋음/보통/아쉬움). 카테고리별 점수·최단거리·개수 동봉(근거 공개).
- `living_score(poi)`: poi `None`(키/좌표 없음)→None, 빈 dict(시설 없음)→0점. complex_detail가 좌표+카카오 키 있을 때 `res["living_score"]` 포함. "거리 기준 참고치" 고지 필수.
