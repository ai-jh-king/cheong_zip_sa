# 앱(스토어) 배포 런북 — Capacitor

> "웹으로 이미 되는데, 스토어 앱으로 내보내려면?"에 대한 **실행 절차**.
> 전략·배경은 `MOBILE_APP_STRATEGY.md`, 여기는 순수 실행 단계.
> ⚠️ 네이티브 빌드·심사는 **개발자 PC(+Android Studio / Mac+Xcode)와 스토어 계정**에서 이뤄진다. 이 저장소는 그 준비(설정·의존성·런북)까지 완료돼 있다.

---

## 0. 지금 상태 (사실)
- ✅ **PWA 완료**: 지금도 모바일 브라우저에서 "홈 화면에 추가"하면 설치형 앱처럼 쓸 수 있다(스토어 없이 즉시 배포된 셈). manifest·아이콘·서비스워커 구비.
- ✅ **웹 빌드(Vite)·백엔드 서빙 완료**.
- ✅ **Capacitor 설정 완료**: `frontend/capacitor.config.json`(appId `com.cheongzipsa.app`, appName 청집사, webDir `dist`), 의존성 `package.json`.
- ⬜ **네이티브 셸 생성·스토어 제출**: 아래 절차(개발자 PC).

## 1. 가장 빠른 배포 = PWA (스토어 불필요, 오늘 가능)
1. 웹을 배포(Render)해 HTTPS 도메인 확보.
2. 사용자에게 "브라우저 → 공유 → 홈 화면에 추가" 안내(iOS Safari / Android Chrome).
- 스토어 심사·계정 없이 설치형 앱 경험. **소프트 런칭·지인 테스트엔 이걸 먼저 쓴다.**

## 2. Android 스토어 앱 (Capacitor)
> 필요: Node.js, Android Studio(SDK), Google Play Console 계정($25 1회).

```bash
cd frontend
npm install                         # capacitor 의존성 포함 설치

# 네이티브 앱은 백엔드가 '같은 출처'가 아니다 → API 절대주소로 빌드(중요)
VITE_API_BASE=https://cheongju-realestate.onrender.com npm run build

npx cap add android                 # 최초 1회 (android/ 폴더 생성)
npx cap sync android                # dist → 네이티브로 동기화
npx cap open android                # Android Studio 열기
```
Android Studio에서: 앱 아이콘·스플래시 지정 → **Build > Generate Signed Bundle(AAB)** → 키스토어 생성·보관(분실 시 업데이트 불가) → Play Console에 AAB 업로드 → 내부 테스트 트랙부터.

## 3. iOS 스토어 앱 (Capacitor) — Mac 필요
> 필요: macOS + Xcode, Apple Developer Program($99/년).
```bash
cd frontend
VITE_API_BASE=https://cheongju-realestate.onrender.com npm run build
npx cap add ios
npx cap sync ios
npx cap open ios                    # Xcode
```
Xcode에서: Signing 팀 설정 → 아이콘/스플래시 → Archive → App Store Connect 업로드 → TestFlight 내부 테스트 → 심사 제출.

## 4. 반드시 맞춰야 할 3가지 (안 하면 앱에서 데이터/지도 안 뜸)
1. **API 절대주소**: 위처럼 `VITE_API_BASE=<배포 URL>`로 빌드. (네이티브는 same-origin이 아니라 blank면 실패)
2. **백엔드 CORS**: `CORS_ORIGINS` 에 `capacitor://localhost, https://localhost, http://localhost` 추가(+웹 도메인). (main.py 주석에 예시 있음)
3. **네이버 지도 도메인 등록**: 네이버 클라우드 콘솔 지도 서비스에 앱 서비스 URL/번들ID 등록(미등록 시 `navermap_authFailure` → 지도만 안 뜸, 나머지는 정상).

## 5. 스토어 심사 준비(컴플라이언스)
- 개인정보처리방침·이용약관 URL(백엔드 `/legal` 제공) → 스토어 등록 정보에 링크.
- 데이터 수집 라벨(App Privacy / Data safety): 위치·계정·사용자콘텐츠 항목 정직하게 신고.
- "실거래가는 참고용·법적효력 없음", "대출은 참고 추정" 등 앱 내 고지 유지(이미 구현).
- 지도/실거래 등 공공데이터 출처표기 유지.

## 6. 업데이트 운영
- **웹/PWA**: 재배포 즉시 반영(심사 없음).
- **네이티브 셸**: 웹 자산만 바뀌면 `npm run build && npx cap sync` 후 재빌드·재제출. (셸 로직 불변이면 웹은 서버 자산 로딩 방식으로 심사 없이 갱신도 가능하나, 스토어 정책 확인 필요)

---
### 요약
- **오늘 당장**: PWA(홈 화면 추가)로 배포 — 스토어 불필요.
- **스토어 앱**: `npm install → VITE_API_BASE 지정 빌드 → npx cap add/sync/open → Android Studio/Xcode에서 서명·제출`. 저장소는 준비 완료, 실제 빌드·심사는 개발자 PC·스토어 계정에서.
