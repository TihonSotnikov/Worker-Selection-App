import os
import tempfile

# Окружение задаётся до импорта приложения: отдельная БД и модель во временном каталоге.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="wsa-tests-")
os.environ["LLM_WARMUP"] = "false"
os.environ["ML_TRAIN_ROWS"] = "3000"

import pytest
from fastapi.testclient import TestClient

from app.ai.llm import LLMUnavailableError

WELDER_EXTRACTION = {
    "full_name": "Пётр Сидоров",
    "experience_years": 6,
    "skills": [
        {"skill": "tig", "years": 5, "evidence": "Аргоном варю пять лет, в основном нержавейка"},
        {"skill": "stainless", "years": 4, "evidence": "Цитата, которой нет в ответах кандидата"},
        {"skill": "cnc_milling", "years": 3, "evidence": "навык чужой профессии"},
    ],
    "certificates": [{"kind": "naks", "level": None, "valid": True, "evidence": "НАКС есть, продлевал весной"}],
    "shift_preference": "day_only",
    "home_zone": "south",
    "has_car": True,
    "stated_commute_minutes": 20,
    "max_commute_minutes": 60,
    "salary_expectation": 120,
    "team_preference": "any",
    "important_amenities": ["canteen", "canteen"],
    "previous_turnovers": 1,
    "summary": "Опытный сварщик TIG, против ночных смен.",
}


class FakeLLM:
    """Подменяет Ollama в тестах: отдаёт заранее заданный JSON."""

    model = "fake"

    def __init__(self, response: dict | None = None, error: Exception | None = None):
        self.response = response or WELDER_EXTRACTION
        self.error = error
        self.calls: list[str] = []

    async def status(self) -> dict:
        return {"available": True, "model": self.model, "detail": "test"}

    async def warmup(self) -> None:
        return None

    async def chat_json(self, system: str, user: str, schema: dict) -> dict:
        self.calls.append(user)
        if self.error:
            raise self.error
        return self.response


@pytest.fixture(scope="session")
def app():
    from main import app as fastapi_app

    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fake_llm(app, client):
    fake = FakeLLM()
    original = app.state.llm
    app.state.llm = fake
    yield fake
    app.state.llm = original


@pytest.fixture
def broken_llm(app, client):
    original = app.state.llm
    app.state.llm = FakeLLM(error=LLMUnavailableError("Ollama не запущена"))
    yield
    app.state.llm = original
