# 개발 호재(Landmark) — 청주 하이퍼로컬 호재 지도

## 개념
청주 특유의 개발 호재(방사광가속기·북청주역·스타필드·CTX 등)를 **위치 + 사실 + 출처**로 보여준다.
전국 앱이 못 다루는 청주 하이퍼로컬 차별화. **구조만 먼저, 데이터는 나중에** 채우는 방식.

## 왜곡 없음 규칙 (필수)
- `status`: confirmed(확정)/ongoing(추진)/planned(계획) — 단계를 사실대로.
- `summary`: 사실만. 집값 상승 단정·투자 권유 금지.
- `source_name`/`source_url`: 출처 필수. 출처 없으면 등록 금지.
- 화면에 단계 뱃지 + 출처 + "투자 판단은 본인 책임" 고지 표시.

## 데이터 채우기 (나중에)
1. `scripts/seed_landmarks.py` 의 `LANDMARKS` 리스트에 호재를 출처·좌표와 함께 작성.
2. `python -m scripts.db_upgrade` (landmarks 테이블 생성, 0018)
3. `python -m scripts.seed_landmarks` (이름 기준 upsert)

## 표시 위치
- ✅ 단지 상세: "주변 개발 호재" 섹션(반경 4km, 거리순, 단계 뱃지·출처). 구현 완료.
- ⏳ 지도 탭: 호재 핀. 백엔드 `/landmarks` 준비 완료. 프런트 핀은 데이터 + 화면 확인 후 안전하게 연결 예정.

## API
- `GET /landmarks` — 활성 호재 전체(지도 핀용)
- `GET /landmarks/near?lat=&lng=&radius=` — 단지 주변(거리순)
- `GET /landmarks/labels` — category/status 라벨

## 모델 (Landmark)
name·category(industry/transport/commercial/residential/public)·status·lat·lng·summary·expected_year·source_name·source_url·sort_order·is_active.
