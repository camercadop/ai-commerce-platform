FROM python:3.14-slim

ARG DOMAIN
ENV DOMAIN=${DOMAIN}

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ app/

CMD ["sh", "-c", "uv run uvicorn app.${DOMAIN}.main:app --host 0.0.0.0 --port 8000"]
