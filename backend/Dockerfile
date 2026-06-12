FROM docker.m.daocloud.io/library/node:22-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/README.md ./README.md

RUN python - <<'PY'
import tomllib
from pathlib import Path

deps = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
    "dependencies"
]
Path("/tmp/requirements.txt").write_text("\n".join(deps) + "\n", encoding="utf-8")
PY

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY backend/scripts ./scripts
COPY --from=frontend-build /frontend/dist ./frontend_dist

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
