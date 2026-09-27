import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ["TESTING"] = "1"

from app.core.enums import ShiftPreference
from app.core.schemas import CandidateVector
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_get_history(client):
    """Тестирует получение истории."""
    response = client.get("/api/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@patch("app.services.analyze_service.ml_predict", new_callable=AsyncMock)
@patch("app.services.analyze_service.extract_from_file", new_callable=AsyncMock)
def test_post_analyze(mock_extract, mock_ml_predict, client):
    """
    Тестирует эндпоинт анализа.
    Патчим там, где функции ИСПОЛЬЗУЮТСЯ (в analyze_service).
    """
    vector = CandidateVector(
        skills_verified_count=3,
        years_experience=2.5,
        age=30,
        commute_time_minutes=40,
        shift_preference=ShiftPreference.ANY,
        salary_expectation=60000,
        has_certifications=True,
        education_level=2,
        previous_turnovers=1,
        family_status=1,
        housing_type=0,
        has_transport=True,
    )

    mock_extract.return_value = ("Test Candidate", "Test Summary", vector)
    mock_ml_predict.return_value = (0.95, ["No risks"])

    files = {"file": ("resume.txt", b"test file content", "text/plain")}
    response = client.post("/api/analyze", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Test Candidate"
    assert data["vector"]["age"] == 30
