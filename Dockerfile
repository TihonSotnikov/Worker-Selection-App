FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN /uv/bin/uv sync --frozen --no-dev --no-install-project

COPY . .

# Ставим PYTHONPATH на корень, чтобы импорты 'app.services...' работали везде
ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
