# 개인화 (skills)

## 정체성 전략 (단계적)
- **1단계(현재)**: 익명 `device_id`(클라이언트 생성, `safeStore`로 localStorage↔메모리 폴백). 개인정보 0.
- **2단계(예정)**: 카카오/네이버 소셜 로그인 → 기기 데이터를 `account_id`로 승격·동기화. 로그인은 선택.
- 민감정보(대출 프로필)는 **별도·동의·암호화/미저장**으로 격리(지침서 9.A).

## 1단계 구현 (완료)
- 모델: `UserPref(device_id, data JSON)`, `RecentView(device_id, target_id, meta, viewed_at)`, `Favorite`.
- API: `/me/prefs`(GET/PUT 설정), `/me/recent`(GET/POST 최근 본 단지, 상한 20), `/favorites`(GET/POST/DELETE).
- 설정 항목(`prefs.data`): `unit`(m2/py), `my_gu`(내 동네). 변경 시 자동 PUT.
- 홈: 내 동네 칩 → 구별 랭킹/실거래/추이가 **내 동네 우선 정렬+하이라이트**. 최근 본 단지 섹션.

## 확장 패턴 (새 개인화 항목 추가 시)
- 단순 설정 → `prefs.data`에 키 추가(별도 테이블 불필요).
- 목록형(저장된 검색·관심 지역) → device 스코프 테이블 추가(예: `SavedSearch(device_id, filters JSON)`), upsert+상한 관리는 `recent` 패턴 참고.
- 프런트: App에서 device 스코프 fetch → 상태 → 낙관적 업데이트 + best-effort 동기화(백엔드 없어도 UI 안 깨짐).
- 로그인 도입 시: 스키마에 `account_id` 컬럼 추가, 로그인 시 device 데이터 이전(merge), 이후 account 우선.

## 주의
- 개인화 데이터에 **이름·연락처 등 PII 저장 금지**(로그인 전까지). device_id는 불투명 난수.
- 추천/맞춤은 **데이터 근거** 기반만(투자 권유·수익 보장 표현 금지).

## 계정 union(이관)
- 로그인 시 device→account 연결(DeviceLink). 읽기/삭제는 owner_device_ids(계정 연결 device 전체) 기준 union.
- 매물은 로그인 시 account_id 흡수(_adopt_device_data). 관심/최근/검색/설정은 union으로 자동 통합(스키마 무변경).
- 프런트: 개인화 호출에 authHeader, account 변경 시 재조회.
