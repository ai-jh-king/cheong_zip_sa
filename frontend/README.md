# 프런트(Vite 빌드) — Phase A

기존 `app/web/index.html`(브라우저 런타임 Babel + CDN)을 **빌드 가능한 Vite 프로젝트**로 옮긴 것입니다.
앱 코드 본문은 **무변경**이며, 바뀐 것은 다음뿐입니다.

- `src/main.jsx` 상단에 `import React` / `createRoot` / `createPortal` 추가(기존 CDN 전역 대체)
- `const API="";` → `const API=(import.meta.env&&import.meta.env.VITE_API_BASE)||"";` (폴백 `""` 동일)
- `index.html` 에서 React/ReactDOM/Babel CDN 제거, 인라인 babel 스크립트 → `<script type="module">`

> 본문이 원본과 **딱 1줄(API)만** 다름은 추출 시 diff 로 검증했습니다.

## 빌드 (운영 산출물)
```bash
cd frontend
npm install
npm run build      # → frontend/dist/ (index.html + 해시된 JS/CSS + public 자산)
```
운영에선 FastAPI 가 `dist/` 를 같은 출처로 서빙 → `API=""` 상대경로 그대로 동작.

## 개발 서버
```bash
npm run dev        # http://localhost:5173 (HMR)
```
- 백엔드를 `http://localhost:8000` 에 띄워 두면 `.env.development` 의 `VITE_API_BASE` 로 호출됩니다.
- 백엔드 CORS 가 dev origin 허용 필요(현재 `["*"]` 라 통과).

## ✅ 검증 체크리스트 (반드시 실제 머신에서)
> 이 작업은 네트워크가 막힌 환경에서 만들어져 **`npm install`/`npm run build` 를 여기서 실행하지 못했습니다.**
> 아래를 개발 머신에서 한 번 돌려 "기능·UI 무변경"을 최종 확인하세요.

1. `npm install && npm run build` 성공(에러 0).
2. `npm run preview` 또는 FastAPI 로 `dist/` 서빙 → 브라우저에서:
   - 홈/시세/단지상세/지도/뉴스/대출/청약/커뮤니티/관심/로그인 **모든 탭 렌더 & 동작**
   - 지도(네이버 SDK 런타임 주입) 정상
   - 차트·QR·포털(모달) 정상 (createPortal 사용처)
   - 데모 폴백(백엔드 미응답 시) 정상
3. 콘솔 에러 0 확인.

## 컷오버(검증 후)
1. FastAPI `WEB_DIR` 를 `frontend/dist` 로 변경(또는 dist 를 web 루트로 배포).
2. `/sw.js` 가 dist 루트에 포함되는지 확인(public/sw.js → dist/sw.js).
3. 검증 끝나면 레거시 `app/web/index.html`(런타임 Babel 버전) 제거.

## 다음(Phase B/C)
- B: `manifest.webmanifest`+아이콘, Pretendard 폰트 로컬 번들(현재는 CDN link 유지).
- C: Capacitor. 이때 `VITE_API_BASE` 를 운영 API 절대 URL 로(네이티브 셸은 같은 출처가 아님).
