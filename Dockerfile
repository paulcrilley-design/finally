# One image for the whole app: scripts/start_mac.sh builds and runs it.

FROM node:24-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1

# Same layout as the repository, so the app's default paths work unchanged:
# /app/backend, /app/frontend/out, /app/db and the optional /app/.env.
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/app ./app
COPY backend/db ./db
RUN uv sync --locked --no-dev
COPY --from=frontend /build/out /app/frontend/out

# A new named volume copies this folder's owner, so the app user can write to it.
RUN useradd --uid 1000 --create-home finally && install -d -o finally /app/db
USER finally

EXPOSE 8000
# Without the shutdown timeout an open price stream blocks shutdown forever.
CMD ["/app/backend/.venv/bin/uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "3"]
