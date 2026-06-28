# skills/testing.md — 테스트·CI 지침

회귀 안전망. 새 기능/버그 수정 시 **테스트를 함께** 추가한다. 유료 서비스의 토대.

## 실행
```bash
pip install -r requirements.txt
pytest                 # 전체
pytest tests/test_loan.py -q
pytest -k community    # 이름 필터
```
CI(.github/workflows/ci.yml)가 push/PR 마다 compile 체크 + pytest 를 돌린다.

## 격리 원칙 (중요)
- `tests/conftest.py`가 **import 전에** `DATABASE_URL`을 버리는 SQLite(`_pytest_tmp.db`)로 강제 지정한다.
  → 절대 개발/운영 DB 에 붙지 않는다. (엔진은 import 시점에 생성되므로 순서가 중요)
- `MOLIT_SERVICE_KEY` 등 외부 키를 빈 값으로 강제 → **테스트는 네트워크를 호출하지 않는다.**
- `_schema`(세션): 테이블 생성/정리. `_clean`(각 테스트): 모든 테이블 truncate 로 테스트 간 격리.
- 픽스처: `db`(세션), `client`(FastAPI TestClient, 의존성은 같은 테스트 엔진 사용).

## 무엇을 테스트하나 (현재)
- `test_loan.py` / `test_costs.py`: 순수 계산(LTV/DSR min·월상환·취득세·중개보수). 외부 의존 없음.
- `test_normalize.py`: dedup_key(금액 포함) vs identity_key(금액 제외) — 정정/해제 매칭 토대.
- `test_cache.py`: stat_cached 메모이즈 + data_version 무효화 + deepcopy 격리.
- `test_stats.py`: 시세 집계(해제분 제외·평균·표본부족 None) — DB 시드.
- `test_community.py`: 원자적 카운터(조회/좋아요/신고)·스크랩 — API(TestClient).
- `test_affordable.py`: 예산 상한·단지 필터·/loan/affordable.
- `test_subscription.py`: 청약 API 폴백(live·notice·구조).
- `test_compare.py`: compare_one 지표·미발견·/compare API.
- `test_corrections.py`: 실거래 정정/해제/멱등/모호.
- `test_gongsi.py`: 공시가격 집계(청주만·중앙값). `test_schools.py`: 학군 요약.
- `test_enrich.py`: K-apt 기본정보 정규화 매핑·누락 None·주차 합산.
- `test_legal.py`: 정책 버전·문서 제공·동의 이력 기록/확인.
- `test_ratelimit.py`: 레이트리미터 허용/차단/윈도 리셋.
- `test_ops.py`: /health(DB핑)·/status/data(신선도)·appmeta 헬퍼.
- `test_notify.py`: 실거래 알림 매칭·커서 중복방지·모의/해제/비로그인 제외.
- `test_api_smoke.py`: 핵심 엔드포인트 200(빈 데이터에서도 안 깨짐).

## 새 테스트 추가 규칙
- 새 집계/계산 로직 → 순수 함수 테스트 우선(가장 빠르고 안정적).
- DB 가 필요하면 `db` 픽스처로 시드, 캐시 함수는 호출 전에 `cache.bump_data_version()`로 무효화.
- 외부 API 는 직접 부르지 말 것(키 비움). 필요하면 응답을 모킹.
- 카운터/상태 변경은 API 레벨에서 검증(원자성·권한·숨김 임계치).
