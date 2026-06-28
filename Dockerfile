# 청주 부동산 플랫폼 — 프로덕션 이미지 (컷오버 확정: 프런트 dist 서빙)
# 멀티스테이지: ①프런트(Vite) 빌드 → ②백엔드 런타임에 dist 포함 + WEB_DIR 고정.
# 웹·스케줄러가 같은 이미지를 공유(스케줄러는 command만 교체, 항상 1개).

# ---- Stage 1: 프런트(Vite) 빌드 ----
FROM node:20-slim AS web-build
WORKDIR /web
# 의존성 먼저(레이어 캐시). lock 파일이 있으면 함께 복사됨.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
# 소스 복사 후 빌드 → /web/dist
COPY frontend/ ./
# 네이티브가 아닌 동일출처 웹이므로 VITE_API_BASE 기본 "" 유지(상대경로 = 백엔드와 같은 출처).
RUN npm run build

# ---- Stage 2: 백엔드 런타임 ----
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 파이썬 의존성(레이어 캐시)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 앱 소스(.dockerignore 가 .env·산출물·node_modules 제외)
COPY . .

# ①에서 빌드된 dist를 이미지에 포함하고 기본 서빙 경로로 지정 → 컷오버 확정.
COPY --from=web-build /web/dist /app/frontend/dist
ENV WEB_DIR=/app/frontend/dist

# 비루트 실행(보안)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 웹 서버(스케줄러는 앱 startup이 아닌 별도 프로세스라 다중 워커 안전).
# 워커/포트는 환경변수로 조정: WEB_CONCURRENCY, PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}
