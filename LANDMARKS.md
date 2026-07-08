# 개발 호재(Landmark) — 청주 하이퍼로컬 호재 지도

## 개념
청주 특유의 개발 호재(방사광가속기·북청주역·스타필드·CTX 등)를 **위치 + 사실 + 출처**로 보여준다.
전국 앱이 못 다루는 청주 하이퍼로컬 차별화. **구조만 먼저, 데이터는 나중에** 채우는 방식.

## 왜곡 없음 규칙 (필수)
- `status`: confirmed(확정)/ongoing(추진)/planned(계획) — 단계를 사실대로.
- `summary`: 사실만. 집값 상승 단정·투자 권유 금지.
- `source_name`/`source_url`: 출처 필수. 출처 없으면 등록 금지.
- 화면에 단계 뱃지 + 출처 + "투자 판단은 본인 책임" 고지 표시.

## 현재 상태 (v1.152)
- **실제 호재 시드 완료**(`scripts/seed_landmarks.py`, 출처 확인): SK하이닉스 P&T7(테크노폴리스·19조·2028)·오창 방사광가속기(2028경)·청주테크노폴리스 산단·북청주역세권(예정)·청주 OSCO(2025). → 운영 DB에 `python -m scripts.seed_landmarks` 1회 실행하면 활성.
- 표시 위치 3곳: ① 단지 상세 "주변 개발 호재"(반경 4km·거리순), ② **홈 "🏗 청주는 지금" 카드**(`CityIssues`, 전체 호재), ③ **지도 "🏗 호재" 토글 핀**(좌표 있는 것만·클릭 시 요약·출처).

## 데이터 채우기·갱신
1. `scripts/seed_landmarks.py` 의 `LANDMARKS` 리스트를 편집(사실·출처·좌표). 좌표 없으면 지도 핀 제외(홈 카드엔 표시).
2. (최초 1회, 테이블 없으면) `python -m scripts.db_upgrade` — head 0018.
3. `python -m scripts.seed_landmarks` (name 기준 upsert·멱등).

## 표시 위치
- ✅ 단지 상세 "주변 개발 호재"(반경 4km·거리순·단계 뱃지·출처).
- ✅ 홈 "🏗 청주는 지금"(`CityIssues` → GET `/landmarks`).
- ✅ 지도 "🏗 호재" 핀(`PriceMarkerMap` showLm → GET `/landmarks`, InfoWindow 요약·출처).

## API
- `GET /landmarks` — 활성 호재 전체(홈 카드·지도 핀)
- `GET /landmarks/near?lat=&lng=&radius=` — 단지 주변(거리순)
- `GET /landmarks/labels` — category/status 라벨

## 모델 (Landmark)
name·category(industry/transport/commercial/residential/public)·status(confirmed/ongoing/planned)·lat·lng·summary·expected_year·source_name·source_url·sort_order·is_active.
