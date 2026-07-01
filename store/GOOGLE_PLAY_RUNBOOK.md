# 구글플레이 출시 실전 순서서 (Capacitor · Android)

> 앱 ID: **com.cheongzipsa.app** (확정 — 스토어 등록 후 변경 불가)
> 앱 이름: **청주시세**
> 방식: Vite 웹빌드 → Capacitor 래핑 → 서명된 AAB → Play Console 업로드
> ⚠️ 이 문서의 명령은 **본인 PC(네트워크·Android Studio 가능한 곳)**에서 실행. 샌드박스에선 불가.

---

## 0. 미리 준비 (1회)

| 항목 | 내용 |
|---|---|
| **Android Studio** | 설치 (Windows 가능). JDK 17 포함됨 |
| **Node.js 18+** | 웹빌드·Capacitor용 |
| **구글플레이 개발자 계정** | $25 (1회). play.google.com/console 에서 가입 |
| **지원 이메일·개인정보처리방침 URL** | 스토어 필수. 방침은 이미 웹에 있음: `https://[도메인]/legal/privacy` |

---

## 1. ⚠️ 가장 중요 — API 주소 박아서 빌드

네이티브 앱은 웹과 **다른 출처**라, API 주소를 빌드에 넣지 않으면 **앱에서 데이터가 안 뜬다**.
`frontend/.env.production` 파일을 만들고:
```
VITE_API_BASE=https://cheongju-realestate.onrender.com
```
(실제 배포 도메인으로. 이게 없으면 앱이 빈 화면.)

---

## 2. 웹빌드 + Capacitor 안드로이드 프로젝트 생성

```cmd
cd frontend
npm install
npm install @capacitor/core @capacitor/cli @capacitor/android
npm run build
npx cap add android
npx cap sync
```
- `npm run build` → `dist/` 생성 (VITE_API_BASE 반영됨)
- `cap add android` → `frontend/android/` 네이티브 프로젝트 생성 (최초 1회)
- `cap sync` → 웹빌드를 앱에 복사 (**빌드 바꿀 때마다 실행**)

이후 웹 수정 시: `npm run build` → `npx cap sync` 만 반복.

---

## 3. 앱 아이콘·스플래시

- 아이콘 원본(512x512 이상 PNG)을 준비 → Android Studio의 Image Asset 또는
  `@capacitor/assets` 플러그인으로 일괄 생성 권장:
  ```cmd
  npm install @capacitor/assets --save-dev
  npx capacitor-assets generate --android
  ```
  (원본을 `frontend/assets/icon.png`, `splash.png`로 두면 각 해상도 자동 생성)
- 스플래시 배경색은 이미 청록(#0F766E)로 설정됨(capacitor.config.json).

---

## 4. 버전·서명 (⚠️ 키스토어 분실 = 앱 영영 업데이트 불가)

**a) 버전**: `frontend/android/app/build.gradle` 의 `versionCode`(정수, 업로드마다 +1), `versionName`("1.0.0").

**b) 서명 키(keystore) 생성 — 딱 1번, 절대 잃어버리면 안 됨**:
```cmd
keytool -genkey -v -keystore cheongzipsa-release.keystore -alias cheongzipsa -keyalg RSA -keysize 2048 -validity 10000
```
→ 나온 `.keystore` 파일 + 비밀번호를 **안전한 곳에 백업**(잃으면 이 앱을 다시는 업데이트 못 함).

**c) Android Studio에서**: Build > Generate Signed Bundle/APK > **Android App Bundle(AAB)** > 위 keystore 선택 > release > 빌드.
→ `app-release.aab` 생성됨. 이걸 업로드.

*(또는 Play App Signing 사용 시 업로드 키만 관리 — 권장. Play Console 안내 따르면 됨.)*

---

## 5. Play Console 등록

1. **앱 만들기** → 이름 "청주시세", 무료, 앱 유형.
2. **스토어 등록정보** → `store/google-play.md`의 문구 복사(간단한 설명·자세한 설명·스크린샷 최소 2장·아이콘 512·피처그래픽 1024x500).
3. **개인정보처리방침 URL** 입력.
4. **앱 콘텐츠**:
   - 데이터 보안(Data safety) → `store/google-play.md` 표 기준 작성. ⚠️ **대출 금융정보 저장 여부** 실제 설정대로(미저장이면 '처리 후 미보관').
   - 콘텐츠 등급 설문 → UGC(사용자 매물/게시글) '예' + 신고/차단 안내.
   - 대상 연령, 광고 포함 여부(현재 광고 없음 → '아니오').
5. **AAB 업로드** → 내부 테스트 트랙부터.

---

## 6. 출시 트랙 (안전 순서)

```
내부 테스트(본인·지인 몇 명) → 비공개 테스트(선택) → 프로덕션(정식 공개)
```
- **내부 테스트 먼저**: 실제 기기에서 데이터·로그인·대출계산 무오류 확인.
- 문제 없으면 프로덕션 제출 → 구글 심사(몇 시간~며칠) → 공개.

---

## 체크리스트 (출시 직전)

- [ ] `.env.production`에 실제 API 도메인 (앱 데이터 뜨는지 실기기 확인)
- [ ] versionCode 정수, 업로드마다 증가
- [ ] keystore + 비밀번호 안전 백업 (2곳 이상)
- [ ] 개인정보처리방침 URL 공개 상태
- [ ] Data safety = 실제 동작과 일치 (특히 대출 민감정보)
- [ ] 스크린샷·아이콘·피처그래픽 준비
- [ ] 내부 테스트에서 핵심 플로우(시세·검색·상세·청약·대출) 무오류

---

## 자주 막히는 곳

- **앱은 켜지는데 데이터가 안 나옴** → `.env.production`의 VITE_API_BASE 누락/오타. 다시 build+sync.
- **CORS 에러** → 백엔드 CORS_ORIGINS에 앱 출처 허용 필요. Capacitor 안드로이드 기본 출처는 `https://localhost` (androidScheme=https). 서버 CORS에 이를 포함하거나, 앱↔API는 서버쪽에서 허용 처리.
- **로그인(카카오/네이버) 안 됨** → 소셜 로그인 리다이렉트에 앱 환경 추가 설정 필요할 수 있음(각 개발자콘솔에 앱 패키지·리다이렉트 등록).
- **iOS는?** → Mac+Xcode 필요. Windows에선 불가. 안드로이드 안정화 후 Mac 확보 시 `npx cap add ios`.
