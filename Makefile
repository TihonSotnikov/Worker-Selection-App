.PHONY: setup run test lint format clean docker-build

PYTHON := uv run python
UVICORN := uv run uvicorn

setup:
	uv sync

run:
	$(UVICORN) main:app --host 127.0.0.1 --port 8000 --reload

test:
	uv run pytest tests/

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache

docker-build:
	docker build -t worker-selection-app .
