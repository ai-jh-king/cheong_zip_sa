# 모바일 앱(스토어) 출시 · 장기운영 전략 — Capacitor 경로

> 확정 경로: **웹앱(단일 코드베이스) → Vite 빌드 → Capacitor 래핑 → iOS·Android 스토어**.
> 목표: **코드베이스 1개**로 웹·iOS·Android를 장기 운영. React Native 전면 재작성은 하지 않음(필요가 분명해지기 전까지).
> 원칙: 요청 범위만 실행 · 왜곡 없음(추정·과장 금지) · step by step · 변경 시 원본 대비 diff로 검증.

---

## 0. 현재 출발점 (확인된 사실)

- 프런트: **단일 파일 `app/web/index.html`**(~3,800줄), 브라우저에서 **Babel 런타임 변환**, CDN 4종 의존(React·ReactDOM·Babel·Pretendard).
- ✅ (v1.166+) **Vite 빌드 완료**(package.json·번들러), **PWA 매니페스트·아이콘·서비스워커·웹푸시(VAPID) 완료**, **Capacitor 설정(capacitor.config.json)·의존성 추가 완료**. → A·B 단계 done. 남은 것은 **C(네이티브 셸 생성·스토어 제출)**. 실행 절차는 `MOBILE_DEPLOY.md`.
- 백엔드: FastAPI REST, 운영 인프라는 이미 강함(doctor·스케줄러·마이그레이션·모니터링·백업·CI).
- 데모 폴백 내장(백엔드 없이도 화면 렌더).

> ✅ 위 공통 선행 조건(번들링·매니페스트)은 완료됨. 지금은 `npx cap add android/ios`부터 시작하면 된다(MOBILE_DEPLOY.md).

---

## 1. 단계(마일스톤) 개요

| 단계 | 내용 | 빌드 위치 | 선행 |
|---|---|---|---|
| **A. 웹 빌드 토대(Vite)** | 런타임 Babel 제거, 의존 번들, `dist/` 산출 | Linux/어디서나 | 없음 |
| **B. PWA 완성** | manifest·아이콘·SW 갱신 → 설치형 | Linux | A |
| **C. Capacitor 셸(Android 먼저)** | 웹 래핑, 내부 테스트 트랙 | Linux | B |
| **D. 네이티브 푸시 + iOS 셸** | FCM/APNs 전환, TestFlight | **macOS/CI 필요** | C |
| **E. 스토어 심사·컴플라이언스** | 개인정보 라벨·심사·제출 | - | D |
| **F. 장기운영 체계** | OTA/라이브업데이트 정책·모니터링·유지보수 | - | E |

> 순서 근거: A가 **가장 큰 위험 제거**(빌드 토대). Android를 iOS보다 먼저 두는 이유 — Android는 Linux/CI에서 빌드 가능, iOS는 **반드시 macOS**가 필요해 환경 의존이 큼.

---

## 2. 단계별 상세

### A. 웹 빌드 토대 (Vite) — *최우선, 최대 위험 제거*
**목표**: 현재와 **화면·동작이 동일**하되, 런타임 Babel·CDN 의존을 없애고 `dist/`로 빌드되게 한다.

- 도입: `package.json` + `vite` + `@vitejs/plugin-react`. (TypeScript는 선택 — 초기엔 JS 유지, 점진 전환)
- 의존 로컬화: React/ReactDOM은 npm 패키지로, Pretendard는 **폰트 파일을 로컬 번들**(CDN 차단·오프라인 대비).
- 전략 선택(둘 중 A1 먼저 권장):
  - **A1 (최소 변경)**: 단일 파일을 거의 유지한 채 Vite 엔트리로 감싸 빌드만 통과시킴 → 가장 빠르고 위험 적음.
  - **A2 (점진 모듈화)**: 컴포넌트를 모듈로 분리(장기 유지보수↑). A1 이후 **시간 날 때마다** 진행.
- API 베이스/데모 폴백: 환경변수(`VITE_API_BASE`)로 분리. 백엔드 미응답 시 데모 폴백은 **그대로 유지**.
- 서빙: 기존 FastAPI가 `dist/`를 서빙하거나, 정적 호스팅. (운영 결정)
- **완료 정의(DoD)**: `npm run build` → `dist/` 생성, 빌드 산출물을 브라우저로 열면 **현재 index.html과 기능 동일**. 괄호/컴포넌트 검증 + 수동 화면 확인.
- ⚠️ 위험: 단일 파일에 전역 함수/컴포넌트가 많아 모듈 경계가 없음 → A1로 "통째 번들"부터. 무리한 분해 금지.

### B. PWA 완성
- `manifest.webmanifest`: `name`·`short_name`·`start_url`·`display:standalone`·`theme_color`·`background_color`·아이콘 세트(192/512/maskable).
- 아이콘·스플래시 원본 1개 → 도구로 전 사이즈 생성(`@capacitor/assets` 재활용 가능).
- iOS 메타: `apple-touch-icon`, 상태바 스타일.
- 서비스워커: Vite 산출물 **해시 파일명**에 맞춰 캐싱 전략 갱신(오프라인 셸 + 업데이트 감지). 기존 `sw.js` 로직 점검.
- **DoD**: 모바일 크롬/사파리에서 "홈 화면에 추가" → 독립 실행(주소창 없는 standalone) 확인.

### C. Capacitor 셸 (Android 먼저)
- 설치: `@capacitor/core` `@capacitor/cli`, `npx cap init`(appId 예: `com.<org>.cheongju`, appName).
- `webDir = dist`. `npx cap add android` → `npx cap sync`.
- 네이티브 필수 처리:
  - **노치/세이프에어리어**(상단 상태바 겹침) — `@capacitor/status-bar` + CSS `env(safe-area-inset-*)`.
  - 외부 링크는 시스템 브라우저로(`@capacitor/browser`), 앱 내 뒤로가기(`@capacitor/app`).
  - `server`/`allowNavigation` 설정으로 API 도메인 허용.
- **CORS 연동**: 앱 origin(`https://localhost`, `capacitor://localhost`)을 백엔드 CORS 허용 목록에 추가. (현재 `allow_origins=["*"]`를 운영 도메인+앱 origin으로 좁히는 작업과 함께)
- **DoD**: Android 에뮬레이터/실기기에서 앱 실행, 핵심 화면(홈·시세·단지·뉴스·대출 등) 동작 + 로그인/관심/커뮤니티 정상.
- 빌드: Gradle, Linux/CI 가능.

### D. 네이티브 푸시 + iOS 셸  *(macOS/CI 필요 구간)*
- 푸시 전환(가장 까다로운 기능 변경):
  - 현재 **웹푸시(VAPID)** → 네이티브 **FCM(Android)+APNs(iOS)** (`@capacitor/push-notifications`).
  - 백엔드: 기존 웹푸시 발송은 **유지**(웹/PWA 사용자용), **FCM/APNs 발송 경로를 추가**. 디바이스 토큰에 `type`(web/fcm/apns) 필드 추가, 발송 시 분기.
  - 카카오 알림톡(정보성)·이메일은 기존 채널 그대로.
- iOS 셸: `npx cap add ios` → **Xcode(macOS) 필수**. APNs 키(.p8)·푸시 권한·번들ID·프로비저닝.
- **DoD**: TestFlight 내부 테스트로 iOS 설치, 푸시 수신(양 OS), 딥링크 동작.
- ⚠️ iOS는 Linux에서 빌드 불가 → **Mac 1대 또는 클라우드 CI**(아래 §3) 반드시 확보.

### E. 스토어 심사 · 컴플라이언스
- 개인정보:
  - **Apple App Privacy / Google Data safety** 작성. 수집 항목 정직 기재 — 계정(이메일), 관심/즐겨찾기, 커뮤니티 글, **푸시 토큰**. **대출 입력값은 서버 미저장(세션)** → 그대로 명시(유리). 위치는 사용 시에만.
  - 개인정보처리방침·약관 **URL 필수**(템플릿 존재 → 운영자 정보 채우고 **법무 검토**).
- iOS **가이드 4.2(최소 기능)** 반려 위험 완화: 네이티브 푸시·오프라인 동작·앱다운 UX 확보(단순 URL 래퍼로 보이지 않게).
- 금융/부동산: **"참고용·금융자문 아님" 고지 유지**(이미 있음) → 심사 위험↓.
- 자산: 아이콘·스플래시·스크린샷(기기별)·설명·연령등급·지원/문의 URL.
- **DoD**: 양 스토어 제출 → 심사 통과. 반려 시 사유별 대응 런북(아래 §5).

### F. 장기운영 체계  *("계속 운영" 핵심*)
- **업데이트 정책 결정(중요)**: Capacitor 앱은 웹 자산을 **빌드 시점에 번들**. UI를 바꾸려면
  - (기본) **스토어 재제출**, 또는
  - **OTA/라이브 업데이트**(웹 자산만 즉시 교체) — Capacitor 라이브업데이트(Appflow) 또는 오픈소스(capgo). 
  - ⚠️ **OTA는 JS/웹 자산만**. 네이티브 코드 변경은 OTA 불가(스토어 정책). Apple도 JS 업데이트는 일정 범위 허용. 정책 한도 내 운영 필수.
- 모니터링: 기존 Sentry(웹) + **네이티브 크래시 리포팅** 추가. `/health`·`/admin/monitor` 유지.
- 유지보수 캐던스: Capacitor/OS 메이저 업그레이드, 플러그인·서명 인증서·APNs 키 만료 관리(달력화).
- 단일 SSOT: **웹(dist)이 진실**, `cap sync`로 네이티브 셸에 반영 → 화면 로직은 한 곳에서만 수정.

---

## 3. 빌드/CI 파이프라인
- **Android**: Linux/CI에서 Gradle 빌드 가능.
- **iOS**: **macOS 필수**. 선택지 — (a) Mac 1대 보유, (b) 클라우드 CI(예: Codemagic/EAS/GitHub macOS 러너). Capacitor용 CI 워크플로(`npm ci → npm run build → npx cap sync → 네이티브 빌드 → 서명 → 스토어 업로드`)는 공개 템플릿 다수.
- 서명: iOS는 App Store Connect API 키, Android는 Play 서비스계정 JSON. **비밀은 CI 시크릿/환경변수**(현 프로젝트 관례와 동일).
- 릴리스 트랙: iOS TestFlight 내부 → 외부 → 정식 / Android 내부테스트 → 비공개 → 프로덕션.

---

## 4. 운영자(당신) 액션 — *제가 대신 못 하는 것*
1. **Apple Developer($99/년)·Google Play($25 1회)** 가입, 번들ID 확보.
2. **macOS 또는 클라우드 CI** 결정(iOS 빌드용).
3. **앱 아이덴티티**: 앱 이름·아이콘·스플래시 원본·스크린샷.
4. **개인정보처리방침·약관 URL** + 법무 검토.
5. **호스팅/도메인 + HTTPS**(웹 자산·API).
6. **푸시 키**: APNs(.p8)·FCM 프로젝트.
7. (선택) 라이브업데이트(OTA) 도입 여부 결정.

## 4-1. 제가 코드로 준비할 수 있는 것 — *각 단계에서 스캐폴딩 제공*
- A: `package.json`·`vite.config`·엔트리 구성, CDN→번들 전환, 데모 폴백/`VITE_API_BASE` 분리.
- B: `manifest.webmanifest`·아이콘 생성 스크립트·SW 갱신.
- C: `capacitor.config`·safe-area CSS·외부링크/뒤로가기 처리, **백엔드 CORS 환경변수화**.
- D: 디바이스 토큰 `type` 스키마·발송 분기(백엔드), 프런트 푸시 등록 코드.
- CI: Capacitor 빌드 워크플로 템플릿.
> ⚠️ **이 환경(네트워크 차단·Mac 없음)에서는 빌드/실행/심사를 못 합니다.** 제가 만드는 건 "실행 가능한 스캐폴딩"이고, **실제 빌드·검증은 당신 개발 머신/CI에서** 해야 합니다.

---

## 5. 위험 & 정직한 한계
- **iOS 빌드 = macOS 필수**(가장 큰 환경 제약).
- **iOS 4.2 반려 위험**: 네이티브 기능(푸시·오프라인) 확보로 완화. 반려 시 기능 보강 후 재제출.
- **런타임 Babel 제거 필수**(성능·신뢰성) → A단계 비협상.
- **푸시 전환 비용**(웹푸시→FCM/APNs)은 단순 작업 아님.
- **OTA 한도**: 네이티브 변경은 OTA 불가, 스토어 정책 준수.
- 규모: 데이터/정보 앱 수준에선 검증된 방식(버거킹·MarketWatch 등). 단 네이티브급 인터랙션이 차별점이 되는 단계가 오면 재평가.

---

## 6. 권장 진행 순서(요약)
**A(Vite 빌드) → B(PWA) → C(Android 셸·내부테스트) → D(푸시+iOS·TestFlight) → E(심사·제출) → F(OTA/운영체계).**
각 단계 끝에 **동작하는 산출물 + DoD 검증**. 다음 단계는 **협의 후 착수**.

> 다음 할 일: **A단계 스캐폴딩**(Vite 빌드 토대)부터. 단, 실제 빌드 검증은 개발 머신에서.
