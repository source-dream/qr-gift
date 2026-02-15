$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "[1/3] 启动后端依赖安装"
if (Get-Command uv -ErrorAction SilentlyContinue) {
  Set-Location "$RootDir\backend"
  uv sync --extra dev
  uv run python scripts/db_upgrade.py
  Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$RootDir\backend'; uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
} else {
  Write-Host "未检测到 uv，使用 pip 作为降级方案"
  Set-Location "$RootDir\backend"
  python -m venv .venv
  & "$RootDir\backend\.venv\Scripts\Activate.ps1"
  pip install -e .
  python scripts/db_upgrade.py
  Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$RootDir\backend'; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
}

Write-Host "[2/3] 启动前端"
Set-Location "$RootDir\frontend"
npm install
npm run dev -- --host 0.0.0.0 --port 5173
