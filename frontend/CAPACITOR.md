# Phase C — Capacitor 셸 (Android 먼저) 실행 런북

> 이 문서의 작업은 **개발 머신에서** 합니다. 샌드박스에선 `npx cap add android`(네이티브 `android/` 생성)·Gradle 빌드를 못 합니다(Android SDK·네트워크 필요).
> **선행 조건: Phase A/B 빌드가 먼저 성공해야 합니다**(`npm run build` → `dist/` 정상, 모든 탭·지도·PWA 확인). 그 위에 Capacitor가 얹힙니다.

---

## 0) 필요한 것 (Android)
- **Node.js 18+**, **JDK 17**
- **Android Studio** + Android SDK(+ 에뮬레이터 또는 실기기)
- (iOS는 Phase D에서 — **macOS + Xcode** 필수, 지금은 제외)

## 1) Capacitor 설치 (최신)
```
cd frontend
npm install @capacitor/core@latest @capacitor/cli@latest
npm install @capacitor/android@latest
# 자주 쓰는 플러그인(권장)
npm install @capacitor/app@latest @capacitor/status-bar@latest @capacitor/splash-screen@latest @capacitor/browser@latest
```
> 설정 파일 `capacitor.config.json` 은 이미 들어 있습니다(webDir=`dist`).

## 2) appId 확정 (⚠️ 한 번 정하면 사실상 영구)
`capacitor.config.json` 의 `"appId"` 를 **본인 소유 도메인 역순**으로 바꾸세요.
- 현재 placeholder: `com.example.cheongju` → 예: `kr.co.청주도메인.app` 형태(영문만).
- ⚠️ 스토어 게시 후 변경하면 **다른 앱**이 됩니다. 처음에 신중히.
- `"appName"` 은 표시 이름(현재 `청주시세`).

## 3) Android 플랫폼 추가 (네이티브 프로젝트 생성)
```
npx cap add android      # → frontend/android/ (Gradle 프로젝트) 생성
```

## 4) 네이티브용 웹 빌드 (API 절대 URL 주입)
네이티브 앱은 같은 출처가 아니므로 **백엔드 절대 URL**이 필요합니다.
```
cp .env.production.example .env.production
#  .env.production 의 VITE_API_BASE 를 실제 백엔드 HTTPS 주소로
npm run build            # → dist/ (이 값이 박힘)
```
> ⚠️ 백엔드 **CORS** 가 앱 origin(`capacitor://localhost`, `https://localhost`)과 위 도메인을 허용해야 합니다.
> 현재 `allow_origins=["*"]` 면 통과합니다. 운영에서 좁힐 때 이 origin들을 꼭 포함하세요.

## 5) 동기화 → 실행
```
npx cap sync             # dist + 설정/플러그인을 android 로 복사 (= npm run cap:sync)
npx cap open android     # Android Studio 열기 (= npm run cap:android)
```
Android Studio에서 에뮬레이터/실기기로 Run ▶.

---

## 6) 노치/세이프에어리어 (네이티브에서 거의 항상 필요한 1곳)
상단 상태바가 헤더 그라데이션과 겹칠 수 있습니다. **웹에선 값이 0이라 영향 없고**, 네이티브에서만 여백이 생깁니다.

`frontend/index.html` 에 두 가지 적용:
1. viewport 메타에 `viewport-fit=cover` 추가:
   ```html
   <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
   ```
2. `<style>` 안에 안전영역 패딩(상단 그라데이션 바가 상태바 아래로):
   ```css
   /* 네이티브 상태바 영역 확보 (웹=0, 영향 없음) */
   body { padding-top: env(safe-area-inset-top); }
   .nav { padding-bottom: env(safe-area-inset-bottom); }
   ```
   (실제 셀렉터는 기기에서 확인하며 조정 — 헤더 래퍼/하단 탭에 맞춰)
> ⚠️ 이 변경은 **레거시가 아니라 `frontend/index.html`** 에만. 적용 후 **기기에서 겹침이 사라지는지** 직접 확인하세요.

## 7) 앱 아이콘·스플래시 (PWA 아이콘 재활용)
```
npm install -D @capacitor/assets
# 1024 아이콘/스플래시 원본을 두고:
npx capacitor-assets generate --android
```
> `public/icons/` 의 기본 아이콘은 기능용입니다. 스토어 전 **디자인 아이콘(1024px)** 으로 교체 권장.

---

## 이 단계의 범위 / 다음
- ✅ 여기까지: Android 셸로 웹앱이 네이티브 앱처럼 실행, 내부 테스트 트랙 업로드 준비.
- ⏭ **Phase D**: 네이티브 푸시(웹푸시 VAPID → FCM/APNs) + **iOS 셸(macOS 필요)** → TestFlight.
- ⏭ **Phase E**: 스토어 심사·개인정보 라벨(App Privacy / Data safety)·제출.
- ⏭ **Phase F**: OTA(라이브 업데이트) 정책·장기 운영. (전체 그림: `../MOBILE_APP_STRATEGY.md`)

## 정직한 한계
- 이 런북의 명령은 **개발 머신에서만** 실행됩니다(샌드박스 네트워크 차단).
- iOS는 이 단계에 없음 — **Mac/Xcode** 확보 후 Phase D.
- `appId`·서명키·푸시키는 운영자 자산이라 코드에 넣지 않습니다(환경/시크릿으로).
