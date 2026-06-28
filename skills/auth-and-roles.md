# 로그인·역할·향후 매물거래 (skills)

## 개인화 2단계 — 소셜 로그인 (구조 준비)
- 공급자: **카카오 / 네이버**. 키는 지도·검색 키와 **별개 앱**일 수 있어 분리: `kakao_login_rest_key`, `naver_login_client_id/secret`, `auth_redirect_base`.
- 현재: `/auth/config`(활성화 여부만). 키 들어오고 배포 도메인 정해지면 OAuth 콜백 구현(지금 가짜로 만들지 않음 = 왜곡 방지).
- 모델: `Account(provider, provider_uid, role, nickname)`, `DeviceLink(device_id, account_id)`.

### OAuth 흐름(구현 시)
1. 앱 → `/auth/{provider}/login` → 공급자 인증 페이지로 redirect.
2. 콜백 `/auth/{provider}/callback?code=` → 토큰 교환 → 공급자 프로필(uid) 획득.
3. `Account` upsert(provider+uid 유니크) → 세션/JWT 발급.
4. **device 데이터 승격(merge)**: 현재 device_id의 Favorite/UserPref/RecentView/SavedSearch를 account로 이전·병합 후 `DeviceLink` 기록. 이후 다른 기기에서 로그인하면 account 기준으로 동기화.
- 민감정보: 대출 프로필은 **로그인해도 서버 중앙저장하지 않는 것을 기본**(현재 기기 localStorage). 서버 저장이 필요하면 동의·암호화·격리(지침서 9.A) 별도 적용.

### 개인정보 원칙
- 로그인 전: PII 저장 0(익명 device_id). 로그인 후에도 최소 수집(닉네임·provider uid 수준).
- 동의 이력·처리방침 페이지 필요(배포 전 법무 검토).

## 역할(Role) 설계
- `user` — 일반 사용자(매수자/매도자). 관심·검색·대출 등 현재 기능.
- `agent` — 중개업자. 향후 매물 등록·관리 권한. **자격 검증**(공인중개사 등록번호 확인) 절차 필요.
- 권한은 `Account.role`로 분기. 화면/기능 노출을 role로 게이팅.

## 향후 매물·거래 기능 (지금 미구현 · 설계만)
> "부동산을 등록하고 사고 팔 수 있는" 자체 매물/거래. 부록 B(피처 플래그) 원칙으로 OFF 상태 준비.

- 신규 모델(도입 시): `Listing(agent_account_id, complex/region, 유형, 거래유형, 가격, 면적, 설명, 상태[등록/거래중/완료], created_at)`,
  `ListingInquiry(listing_id, user_account_id, message)`, `Deal(listing_id, buyer, agent, 체결가, 체결일)`.
- **거래↔중개업소 연결**: 자체 플랫폼에서 체결된 `Deal`은 등록 `agent`와 연결됨(출처가 명확). 
  ⚠️ **국토부 실거래(MOLIT) 데이터에는 중개업소 정보가 없다** → MOLIT 거래를 특정 중개사와 연결하지 말 것(왜곡). 인근 중개업소(카카오 AG2)는 '참고'로만 표시.
- 피처 플래그 `features.marketplace`(기본 OFF). 광고/제휴와 마찬가지로 슬롯·모델 자리만 준비, 결정 시 켠다.

## 진행 메모
- 2단계 현재 구현: 대출 프로필 저장(기기 로컬·동의), 맞춤 추천(관심·내 동네 기반·데이터 한정), 로그인 구조 스캐폴드.
- 다음: 키 확보 시 OAuth 콜백 + device 머지 구현 → 그 후 매물/거래(역할 기반).

## 구현됨(로그인)
- 세션 토큰: `app/core/security.py`(HS256, 의존성 없음). 배포 시 JWT_SECRET 필수.
- `/auth/config|login/{p}|callback/{p}|dev-login|me|role|logout`. dev-login은 AUTH_DEV_LOGIN으로 게이트.
- 다른 라우터는 `account_from_auth(db, authorization)`로 Bearer→계정 해석(매물에서 사용).
- 프런트: `getToken/setToken/authHeader`, App에서 #token 캡처→/auth/me. role 전환 시 토큰 재발급.
