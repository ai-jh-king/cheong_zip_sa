#!/usr/bin/env bash
# 한 번 실행: 가상환경 생성 → 의존성 설치 → 데이터 수집 → UI 자동 오픈
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "[1/3] 가상환경 생성…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/3] 의존성 설치…"
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "[3/3] 실행 (브라우저가 자동으로 열립니다)…"
python run.py "$@"
