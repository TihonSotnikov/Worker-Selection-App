from pydantic import BaseModel, Field

from app.core.enums import ShiftPreference


class CandidateVector(BaseModel):
    """
    Полный вектор данных кандидата (12 признаков) для ML-модели.
    """

    skills_verified_count: int = Field(..., ge=0)
    years_experience: float = Field(..., ge=0.0)
    age: int = Field(..., ge=18, le=80)
    commute_time_minutes: int = Field(..., ge=0)
    shift_preference: ShiftPreference = Field(...)
    salary_expectation: int = Field(..., ge=0)
    has_certifications: bool = Field(...)

    # Новые признаки из расширенного контракта
    education_level: int = Field(..., ge=0, le=3, description="0:Среднее, 1:Спец, 2:Колледж, 3:Высшее")
    previous_turnovers: int = Field(..., ge=0, description="Кол-во смен работы")
    family_status: int = Field(..., ge=0, le=3, description="0:Нет, 1:Брак, 2:Дети, 3:Один")
    housing_type: int = Field(..., ge=0, le=3, description="0:Свое, 1:Аренда, 2:Общага, 3:Родители")
    has_transport: bool = Field(..., description="Наличие личного транспорта")


class CandidateSummary(BaseModel):
    """Суммаризация от LLM модели."""

    full_name: str
    raw_summary: str
    vector: CandidateVector


class CandidateResult(BaseModel):
    """Финальный результат анализа."""

    id: str
    full_name: str
    raw_summary: str
    vector: CandidateVector
    retention_score: float
    risk_factors: list[str]
