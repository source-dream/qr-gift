# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

QRGift is a private-deploy gift/red-packet QR code platform. The frontend is a Vue 3 admin console for managing gifts, red packets, security settings, logs, storage configuration, and dashboard data. The backend is a FastAPI REST service that handles auth, QR code generation, red-packet binding/dispatch, scan redirects, audit logs, storage configuration, and SQLite persistence.

Important source docs already in the repo:
- `README.md`: product overview, safety notes, quick start, roadmap, license.
- `docs/ARCHITECTURE.md`: Chinese architecture notes, API inventory, CSV format, storage/security details.
- `AGENTS.md`: detailed agent guidance and style conventions; keep this file and `AGENTS.md` in sync when commands or architecture change.

No Cursor or Copilot rule files were present when this file was created (`.cursor/rules/`, `.cursorrules`, `.github/copilot-instructions.md`). If any are added, read and incorporate them before making substantial changes.

## Where to run commands

- Backend commands: run from `backend/`.
- Frontend commands: run from `frontend/`.
- Docker Compose commands: run from `deploy/`.

## Common commands

### Full local startup

```bash
bash scripts/dev-linux.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-windows.ps1
```

The scripts install dependencies, run database migrations, start the backend on port `8000`, and start Vite on port `5173`.

### Backend setup, run, and database

```bash
cd backend
uv sync --extra dev
uv run python scripts/db_upgrade.py
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Fallback without `uv`:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
python scripts/db_upgrade.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Reset the local admin password:

```bash
cd backend
uv run python scripts/reset_admin.py --username admin --password 新密码
```

### Backend quality checks and tests

```bash
cd backend
uv run black app scripts
uv run ruff check app scripts
uv run ruff check --fix app scripts
uv run mypy app
uv run pytest
```

Single-test examples:

```bash
cd backend
uv run pytest tests/test_xxx.py -q
uv run pytest tests/test_xxx.py::test_name -q
uv run pytest tests/test_xxx.py::test_name[param] -q
```

`pytest` is configured in `pyproject.toml`, but there may be no committed test files yet.

### Frontend setup, run, and build

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
npm run type-check
npm run build
npm run preview
```

There is no configured frontend lint, format, or test script in `frontend/package.json`. Add the corresponding single-test command here if a frontend test runner is introduced.

### Docker deployment

```bash
cd deploy
docker compose up -d --build
```

The compose stack exposes the API/app on host port `2026` by default and stores SQLite/object data in the `qrgift_data` volume.

## Backend architecture

- `app/main.py` creates the FastAPI app, enables permissive CORS, records access logs for admin and scan traffic, mounts API routers, and serves a bundled SPA from `frontend_dist` when present.
- `app/core/` holds shared infrastructure: environment settings, SQLite session setup, auth dependencies/security helpers, crypto helpers, and response envelopes. Settings are read from `.env`/environment via Pydantic Settings; SQLite defaults to `./data/qrgift.db` and uses WAL plus foreign keys.
- `app/api/` is the HTTP boundary. Route handlers validate requests, depend on `get_db` and auth where needed, translate service/repository errors into `HTTPException`, and return the stable `ok(...)` response envelope.
- `app/services/` contains business workflows such as gift creation, QR rendering/upload, red-packet binding, claim dispatch, storage config, and security-rule behavior.
- `app/repositories/` centralizes SQLAlchemy query/update operations used by services and APIs.
- `app/models/` defines SQLAlchemy 2 typed ORM models; `app/schemas/` defines Pydantic request/response contracts.
- `alembic/` and `scripts/db_upgrade.py` manage database migrations. `db_upgrade.py` also handles legacy databases that have business tables but no Alembic version record.
- `app/storage/` defines a storage abstraction with local, MinIO, and Aliyun OSS implementations. Runtime storage channel config can be selected from DB-backed system configuration; QR upload code fails over across available channels.

Core data flow: authenticated admin actions call `/api/*` routes, routes call services/repositories, services update SQLite models and write audit logs, and generated QR images are stored through the storage abstraction. Public scans hit `/r/{token}` and are resolved by the redirect/gift service path, which enforces activation/expiry/status rules, marks successful claims, records claim logs, and returns or redirects to the red-packet target/content.

## Frontend architecture

- `src/main.ts` wires Vue, Pinia, router, and global styles.
- `src/router/index.ts` defines `/login` plus authenticated admin routes under `AppShell`; route guards redirect unauthenticated users to `/login`.
- `src/api/client.ts` creates the Axios client with `VITE_API_BASE_URL || '/api'`, attaches the bearer token from localStorage, and clears auth state on HTTP 401.
- `src/api/modules/*` centralizes typed API calls by domain. Keep backend response/path changes synchronized with these modules.
- `src/stores/auth.ts` owns login/logout token state; `src/stores/theme.ts` owns theme state.
- `src/views/*` are route-level screens for dashboard, gifts, red packets/import, logs, security, system config, and placeholder management views. Shared layout lives under `src/components/layout/`.
- Vite proxies `/api` and `/r/` to `http://127.0.0.1:8000` during development.

## Conventions and safety notes specific to this repo

- Backend targets Python 3.11+, Black/Ruff line length is 100, Ruff rules are `E,F,I,B,UP`, and imports should use `app.*` absolute paths.
- Preserve backend layering: keep HTTP concerns in `app/api`, business rules in `app/services`, and query details in `app/repositories`.
- Keep the `ok(data, message, code)` response envelope stable unless updating all frontend consumers.
- Use SQLAlchemy 2 typed ORM style (`Mapped`, `mapped_column`) and Pydantic field validation for schemas.
- Frontend uses Vue Composition API with `<script setup lang="ts">`, Pinia, Vue Router, single quotes in TypeScript, and centralized API contracts in `src/api/modules/*`.
- Reuse frontend theme tokens in `src/styles/tokens.css` and existing global surfaces in `src/styles/main.css` instead of introducing unrelated hard-coded styling.
- Endpoint paths and response shapes are coupled to the frontend API modules; migrate both sides together.
- For schema changes, add an Alembic migration and verify `uv run python scripts/db_upgrade.py`.
- This app handles money-adjacent and sensitive gift data; README advises private deployment, strong passwords, limited QR sharing, and shutting the service down after use when appropriate.
