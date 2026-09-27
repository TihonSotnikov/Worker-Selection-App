from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(UTC)


class VacancyTable(SQLModel, table=True):
    """Вакансия. Все поля предметной области лежат в JSON (см. VacancyData)."""

    __tablename__ = "vacancies"

    id: int | None = Field(default=None, primary_key=True)
    profession: str = Field(index=True)
    data: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))


class CandidateTable(SQLModel, table=True):
    """Кандидат. Профиль лежит в JSON (см. CandidateProfile)."""

    __tablename__ = "candidates"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_now)
    source: str
    profession: str = Field(index=True)
    full_name: str
    vacancy_id: int | None = Field(default=None, foreign_key="vacancies.id")
    transcript: str | None = None
    profile: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))


class InterviewTable(SQLModel, table=True):
    """Сессия интервью: сценарий вопросов и ответы кандидата."""

    __tablename__ = "interviews"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_now)
    vacancy_id: int = Field(foreign_key="vacancies.id")
    status: str = "active"  # active | ready | done | failed
    step: int = 0
    questions: list[dict[str, Any]] = Field(sa_column=Column(JSON, nullable=False))
    messages: list[dict[str, Any]] = Field(sa_column=Column(JSON, nullable=False))
    candidate_id: int | None = Field(default=None, foreign_key="candidates.id")
    error: str | None = None
