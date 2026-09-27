FROM python:3.11-slim-bookworm

# ffmpeg нужен для расшифровки аудио (faster-whisper)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY main.py ./
COPY app ./app
COPY examples ./examples

# LLM работает на хосте в Ollama; из контейнера она доступна по host.docker.internal
ENV LLM_BASE_URL=http://host.docker.internal:11434 \
    DATA_DIR=/app/data

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
