# QUICKSTART — 백엔드 PC에서 띄우기 (v1.65)

> 원칙: 왜곡 없음 · 대규모 전제 · step by step. 막히면 각 단계 출력을 그대로 확인하세요.
> 상세는 OPERATIONS.md / DATA.md / skills/ 참조.

## 0) 사전 준비 (이미 있다고 확인됨)
- Python · PostgreSQL · 국토부 실거래가 API 키(공공데이터포털)

## 1) 가상환경 + 의존성
```
cd cheongju-realestate
python -m venv .venv
.venv\Scripts\activate            (Windows)
pip install -r requirements.txt
```

## 2) 환경설정(.env)
```
copy .env.example .env            (Windows)
```
.env 에서 최소 다음을 채움:
- `MOLIT_SERVICE_KEY=` (국토부 실거래가 키 — 필수)
- `DATABASE_URL=postgresql+psycopg://cheongju:비번@localhost:5432/cheongju`
- (선택) KAKAO_REST_API_KEY, ADMIN_TOKEN 등

## 3) DB 준비 (PostgreSQL)
```
psql -U postgres -c "CREATE USER cheongju WITH PASSWORD '비번';"
psql -U postgres -c "CREATE DATABASE cheongju OWNER cheongju ENCODING 'UTF8' TEMPLATE template0;"
```
스키마 생성(마이그레이션):
```
python -m scripts.db_upgrade upgrade head
```

## 4) 자가진단 (가장 중요 — 뭐가 빠졌는지 한 번에)
```
python -m scripts.doctor
```
- ❌ 있으면 그 항목부터 해결(메시지가 방법 안내). 전부 ✅/⚠️면 다음으로.

## 5) 실거래 데이터 수집 (최초 1회 필수 — 안 하면 시세가 빔)
```
python -m scripts.run_collect
```
- 청주 4개 구 실거래를 받아 DB에 적재. 완료 후 doctor 의 "데이터 신선도"가 채워짐.

## 6) 서버 실행 (앱 연결하려면 0.0.0.0)
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- 브라우저에서 `http://localhost:8000/health` → ok 확인
- 웹 UI: `http://localhost:8000/`

## 7) 웹 프런트(Vite) — UI 정본 · Node.js 18+
> 모든 UI/기능 수정의 **권위 소스는 `frontend/src/main.jsx`**(Vite). 운영 배포·PWA·스토어가 같은 `dist`를 공유합니다.
> 백엔드만 bare 실행(6번)하면 레거시 `app/web/index.html`이 폴백으로 동작하지만, **편집은 `frontend/src`에서만**(레거시는 동결).
```
cd frontend
npm install
npm run dev        # http://localhost:5173 (백엔드 8000과 자동 연동 / 미연결 시 데모 폴백)
npm run build      # → frontend/dist (운영 산출물)
npm run preview    # 빌드 결과 로컬 서빙
```
- PWA(설치형)·서비스워커는 `localhost`가 보안 출처라 HTTPS 없이도 테스트됩니다(크롬 DevTools → Application 탭에서 Manifest·Service Worker 확인).
- 검증 후 컷오버(백엔드가 `dist` 서빙)·세부 절차는 `frontend/README.md` 참조.

## 8) 네이티브 앱(스토어) — Phase C 이후
- 경로: 웹 → Vite → **Capacitor**(iOS·Android). 단계·요건은 `MOBILE_APP_STRATEGY.md`.
- ⚠️ 과거 안내의 Expo(`cheongju-mobile`)는 **폐기된 계획**입니다(현재 미사용).

## 9) (선택) 자동 수집·백업 스케줄러
```
python -m scripts.scheduler
```

---
막히는 단계의 출력/에러를 그대로 공유하면 거기서 정확히 잡습니다.
