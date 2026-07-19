# 소셜 로그인 진단 (카카오·네이버)

> 카카오·네이버 로그인 에러 시 순서대로 확인. 대부분 **①환경변수 미설정 or ②콘솔의 리다이렉트 URI 불일치**.

## 0. 코드 수정(v1.174 → 1.175)
- 이번 릴리스에서 `redirect_uri`·`state` 를 `urllib.parse.quote(safe="")` 로 인코딩. 콘솔 등록값과 문자 단위로 일치해야 하는 카카오·네이버 요구사항 준수. **이 수정만으로 문제가 사라질 수 있음** — 배포 후 다시 시도.

## 1. Render 환경변수(웹 서비스 > Environment) 필수 5종
```
AUTH_REDIRECT_BASE=https://cheongju-realestate.onrender.com     # 슬래시 없이. 실제 서비스 도메인.
KAKAO_LOGIN_REST_KEY=<카카오 개발자센터 REST API 키>
NAVER_LOGIN_CLIENT_ID=<네이버 개발자센터 Client ID>
NAVER_LOGIN_CLIENT_SECRET=<네이버 개발자센터 Client Secret>
JWT_SECRET=<32자 이상 무작위>
```
> 하나라도 비면 `/auth/login/{provider}` 가 400 반환 → 프런트에서 "로그인 설정이 필요합니다" alert.
> **확인법**: 배포 도메인/`/auth/config` 접속 → `providers.kakao / providers.naver` 값이 `true` 여야 함(둘 다 false면 위 env 누락).

## 2. 콘솔의 리다이렉트 URI — 문자 단위 일치 필수(mismatch 원인 1위)

### 카카오 (developers.kakao.com)
1. 앱 선택 → **제품 설정 > 카카오 로그인**
2. **활성화 상태 = ON** 인지 확인 (많이 놓침).
3. **Redirect URI**: 반드시 아래와 정확히 일치(대소문자·슬래시·프로토콜 포함):
   ```
   https://cheongju-realestate.onrender.com/auth/callback/kakao
   ```
4. **동의항목**: `profile_nickname` 정도만 필수(다른 건 심사 필요) — 서버 코드가 그 이상 요구 안 함.
5. **REST API 키**를 env `KAKAO_LOGIN_REST_KEY` 에. (JavaScript 키 아님)

### 네이버 (developers.naver.com)
1. **Application > 내 애플리케이션** 에서 앱 선택.
2. **API 설정** 에서 **"네이버 아이디로 로그인"** 사용 설정.
3. **서비스 URL** 과 **Callback URL** 등록:
   - 서비스 URL: `https://cheongju-realestate.onrender.com`
   - Callback URL: `https://cheongju-realestate.onrender.com/auth/callback/naver`
4. **Client ID/Secret** 를 각각 env 에.

## 3. 프런트 확인
- 로그인 버튼 자체가 안 보임 → `/auth/config` 응답의 `providers.*` 가 false → env 문제(§1).
- 버튼 눌러 "로그인 설정이 필요합니다" alert → `AUTH_REDIRECT_BASE` 나 provider 키 누락(§1).
- 카카오·네이버 화면으로 이동은 됨 → 다음 절 §4.

## 4. 콜백 단계에서 실패(로그인 화면까진 가는데 되돌아와서 `?login=error`)
정확한 원인은 카카오/네이버 화면의 에러 코드에 나옵니다:

| 화면에 뜨는 에러 | 원인 | 해결 |
|---|---|---|
| `KOE006` / `redirect_uri_mismatch` | 콘솔 등록 URI ≠ 앱이 보낸 URI | §2 URI 문자 단위 일치. `AUTH_REDIRECT_BASE`에 슬래시 있는지 확인 |
| `KOE101` / `invalid_client` | 앱 상태 OFF 또는 키 다름 | 카카오 로그인 활성화 상태 ON, REST API 키 재확인 |
| `unauthorized_client` (네이버) | Callback URL 미등록/오타 | §2 재확인 |
| 프로필 조회 실패 → `?login=error` | 스코프 부족·토큰 만료 | 재시도. 반복되면 콘솔 동의항목 확인 |

## 5. 최후 확인 — 최소 예시로 격리 테스트
Render Shell:
```bash
python -c "
from app.core.config import get_settings; s=get_settings()
print('redirect_base:', s.auth_redirect_base)
print('kakao_key set :', bool(s.kakao_login_rest_key))
print('naver_id set  :', bool(s.naver_login_client_id))
print('naver_sec set :', bool(s.naver_login_client_secret))
"
```
모든 값이 True/실값이어야 정상.

## 6. 임시 우회(원인 좁힐 때만)
`AUTH_DEV_LOGIN=true` 로 두면 `/auth/dev-login` 으로 로그인 가능(개발용). **소셜 로그인 문제 격리에만 쓰고 실배포엔 절대 false 유지**.


## 7. v1.176 기준 로컬 진단 절차(정확한 원인 파악)
1. `/auth/config` 응답 확인 → `providers` 둘 다 `true` 가 나오면 env·키는 정상.
2. 카카오/네이버 버튼을 눌러 로그인 시도.
3. 실패로 앱에 돌아오면 **URL 을 확인** — v1.176 부터 실패 사유가 붙습니다:
   ```
   http://127.0.0.1:8000/?login=error&provider=kakao&why=<사유>
   ```
   `why=` 부분을 URL 디코드해서 붙여주면 원인 확정. 예: `kakao token 실패: KOE320`, `naver token 실패: invalid_request`.
4. **서버 로그**(uvicorn 실행 창)에도 `auth.oauth` 로거로 상세 스택 남음. 그것도 확인.

### 카카오 콘솔 필수 확인(로그인 화면 후 에러 나는 경우)
- **동의항목**: `프로필 정보 (닉네임/프로필 사진)` → **필수 동의** 로 켜져 있어야 `me["id"]` 응답. OFF 면 프로필 조회 실패 → v1.176 이후 사유가 URL 에 노출됨.
- **Client Secret 사용** ON 인 앱이면 env `KAKAO_LOGIN_CLIENT_SECRET` 설정 필요. OFF 이면 비워두면 됨.

### 네이버 콘솔 필수 확인(들어가자마자 에러)
- **사용 API 에 '네이버 아이디로 로그인' 추가·활성화**(빠진 앱이 흔함).
- **PC 웹 서비스 URL / Callback URL 등록**:
  - 서비스 URL: `http://127.0.0.1:8000` (로컬) 또는 배포 도메인
  - Callback URL: 위 + `/auth/callback/naver`
- 네이버 에러 페이지 URL 파라미터(`error=...&error_description=...`)를 붙여주면 원인 확정.
