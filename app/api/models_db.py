import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class CandidateTable(SQLModel, table=True):
    """Таблица для хранения 12 признаков кандидата."""

    __tablename__ = "candidates"

    id: str | None = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        nullable=False,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    full_name: str
    raw_summary: str
    retention_score: float
    risk_factors: str

    # Вектор признаков (12 полей)
    vec_skills_count: int
    vec_years_experience: float
    vec_age: int
    vec_commute_minutes: int
    vec_shift_preference: int
    vec_salary_expectation: int
    vec_has_certifications: bool
    vec_education_level: int
    vec_previous_turnovers: int
    vec_family_status: int
    vec_housing_type: int
    vec_has_transport: bool
