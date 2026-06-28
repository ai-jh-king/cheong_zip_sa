# CUTOVER — 레거시 HTML → Vite dist 서빙 전환

> 목적: 웹 UI를 레거시 단일 파일(`app/web/index.html`)에서 **Vite 빌드(`frontend/dist`)** 서빙으로 전환하여 **소스를 한 곳(`frontend/src/`)으로 일원화**한다.
> 이후 모든 UI/기능 수정은 `frontend/src/`에서만 → `npm run build` → 배포(웹·PWA·Capacitor가 같은 `dist` 공유).

## ✅ 확정 상태 (프로덕션 이미지 기준)
- **프로덕션 컨테이너는 dist를 서빙하도록 확정됨.** `Dockerfile`이 **멀티스테이지**(① Vite 빌드 → ② 백엔드 런타임에 `dist` 포함 + `ENV WEB_DIR=/app/frontend/dist`). 즉 `docker build` 시 프런트가 빌드되고, 그 이미지는 **단일 소스(`frontend/src`)에서 나온 dist**를 서빙한다.
- **단일 소스 전환 완료**: 이제 모든 UI/기능 수정은 **`frontend/src/`에서만** → `npm run build` → 배포. 레거시 `app/web/index.html`은 **동결(편집 금지)**, 로컬 bare 실행의 폴백으로만 잔존.
- 메커니즘(공통): `app/main.py`의 `WEB_DIR` 환경변수. dist(assets/ 보유) 지정 시 `SPA_MODE`로 `/assets`·manifest·icons 정적 마운트(명시 라우트·API가 우선, 가리지 않음). bare 로컬에서 미설정 시 레거시 폴백.

> ⚠️ **남은 단 하나의 미검증 지점**: 샌드박스에선 도커 빌드·기동 불가 → **운영 머신에서 컨테이너를 띄워** 아래 "검증 체크리스트"로 라우트·자산이 정상인지 1회 확인. 통과하면 컷오버 完了.

## (참고) bare 로컬에서 수동 전환·롤백
컨테이너 없이 로컬에서 dist 서빙을 시험할 때:
```
# 1) 빌드
cd frontend
npm run build                         # → frontend/dist (index.html, assets/, sw.js, manifest, icons)

# 2) 백엔드를 dist로 서빙 (절대경로 권장)
cd ..
export WEB_DIR="$(pwd)/frontend/dist"  # Windows PowerShell: $env:WEB_DIR="$PWD\frontend\dist"
uvicorn app.main:app --port 8000       # 또는 python run.py

# 3) 확인 → http://localhost:8000
```

## 검증 체크리스트 (런타임 — 개발 머신 필수)
- [ ] `/` → **새 빌드 화면**이 뜸(레거시와 동일 모양)
- [ ] DevTools Network: `/assets/*.js`·`*.css` **200**, `/manifest.webmanifest` 200, `/icons/*` 200
- [ ] API 안 가려짐: `/health`·`/config`·`/transactions`·`/dashboard/*` 정상(마운트가 라우트보다 후순위)
- [ ] `/sw.js` 200 (PWA·푸시)
- [ ] 모든 탭·지도·모달·차트·공유 QR·데모폴백이 **레거시와 동일**
- [ ] 콘솔 에러 0
> 위 항목은 `TESTING.md` D(빌드)·E(PWA)와 함께 수행.

## 롤백 (즉시·코드 변경 0)
```
unset WEB_DIR          # PowerShell: Remove-Item Env:\WEB_DIR
# 서버 재시작 → 즉시 레거시(app/web) 복귀
```
문제가 보이면 env만 끄면 원상복구됩니다. 코드는 그대로 둬도 안전(기본=레거시).

## 컷오버 이후 (소스 일원화)
- ✅ 모든 UI/기능 수정 → `frontend/src/`에서만 → `npm run build` → 배포.
- 레거시 `app/web/index.html`은 **즉시 삭제하지 말고** 한 배포 사이클 병행 후 동결/아카이브(롤백 여유). 안정화되면 제거.
- (선택) 3,700줄 `main.jsx`를 `components/`·`hooks/`·`api/`로 **모듈 분리**(빌드 위에서 동작 동일). 유지보수성 향상.
- `scripts/verify_frontend.py`는 컷오버 전까지의 무결성 도구 → 컷오버·모듈분리 후엔 역할 종료(문서에 명시).

## 영향 범위 / 주의
- **CORS/도메인**: 같은 출처(백엔드가 dist 서빙)면 영향 없음. 네이티브 앱(다른 출처)은 별도 — `frontend/CAPACITOR.md`.
- 정적 파일 캐시 헤더가 필요하면(운영 성능) 리버스 프록시(Nginx 등)에서 `/assets`에 long-cache 설정 권장(파일명 해시이므로 안전).
