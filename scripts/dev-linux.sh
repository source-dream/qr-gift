#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/3] 启动后端依赖安装"
if command -v uv >/dev/null 2>&1; then
  (cd "$ROOT_DIR/backend" && uv sync --extra dev)
  (cd "$ROOT_DIR/backend" && uv run python scripts/db_upgrade.py)
  (cd "$ROOT_DIR/backend" && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
else
  echo "未检测到 uv，使用 pip 作为降级方案"
  (cd "$ROOT_DIR/backend" && python3 -m venv .venv)
  # shellcheck disable=SC1091
  source "$ROOT_DIR/backend/.venv/bin/activate"
  (cd "$ROOT_DIR/backend" && pip install -e .)
  (cd "$ROOT_DIR/backend" && python scripts/db_upgrade.py)
  (cd "$ROOT_DIR/backend" && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
fi

echo "[2/3] 启动前端"
(cd "$ROOT_DIR/frontend" && npm install && npm run dev -- --host 0.0.0.0 --port 5173)
