.PHONY: setup model stt-model run test lint format reset clean docker-build

LLM_MODEL ?= qwen3.5:9b
STT_MODEL ?= large-v3-turbo

setup:  ## Зависимости Python + локальная LLM + модель распознавания речи
	uv sync
	$(MAKE) model
	$(MAKE) stt-model

model:  ## Скачать LLM для Ollama (нужен запущенный Ollama)
	ollama pull $(LLM_MODEL)

stt-model:  ## Заранее скачать модель faster-whisper (~1.6 ГБ), чтобы первая загрузка аудио не ждала
	uv run python -c "from faster_whisper import WhisperModel; WhisperModel('$(STT_MODEL)', device='cpu', compute_type='int8')"

run:  ## Запуск приложения: http://127.0.0.1:8000
	uv run uvicorn main:app --host 127.0.0.1 --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

reset:  ## Сбросить базу и модель удержания — пересоздадутся при следующем запуске
	rm -f data/app.db data/retention_model.cbm data/retention_model.json

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache

docker-build:
	docker build -t worker-selection-app .
