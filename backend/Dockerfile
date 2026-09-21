FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS build

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-editable

COPY src ./src
RUN uv sync --locked --no-dev --no-editable


FROM python:3.13-slim-bookworm

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    BRANDS_DIR=/app/brands \
    DATA_DIR=/app/data \
    OUTPUT_DIR=/data/out \
    DATABASE_PATH=/data/listforge.db

RUN useradd --create-home --uid 10001 listforge && install -d -o listforge /data
WORKDIR /app

COPY --from=build --chown=listforge:listforge /app/.venv /app/.venv
COPY --chown=listforge:listforge brands ./brands

USER listforge
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "list_forge.api:app", "--host", "0.0.0.0", "--port", "8000"]
