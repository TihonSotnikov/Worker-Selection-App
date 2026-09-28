"""
Pydantic-схемы предметной области и ответов API.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.core.enums import (
    Amenity,
    CandidateSource,
    CertKind,
    CheckStatus,
    Profession,
    RiskLevel,
    ShiftPreference,
    ShiftSchedule,
    TeamFormat,
    TeamPreference,
    Zone,
)

# ---------------------------------------------------------------------------
# Кандидат
# ---------------------------------------------------------------------------


class SkillClaim(BaseModel):
    """Навык, который кандидат назвал на интервью."""

    skill: str
    years: float | None = None
    evidence: str = ""
    verified: bool = False  # цитата есть в ответах кандидата и относится к навыку
    # found — цитата найдена и про этот навык; not_found — в ответах её нет;
    # off_topic — цитата есть, но не про этот навык; "" — синтетический профиль
    evidence_status: str = ""


class CertClaim(BaseModel):
    """Удостоверение, которое назвал кандидат."""

    kind: CertKind
    level: int | None = None
    valid: bool = True
    evidence: str = ""


class CandidateProfile(BaseModel):
    """Полный профиль кандидата: навыки + профиль комфорта + стабильность."""

    full_name: str
    profession: Profession
    summary: str = ""
    experience_years: float | None = None
    previous_turnovers: int | None = Field(None, description="Смен места работы за последние 5 лет")
    skills: list[SkillClaim] = []
    certificates: list[CertClaim] = []

    shift_preference: ShiftPreference = ShiftPreference.UNKNOWN
    home_zone: Zone | None = None
    has_car: bool | None = None
    max_commute_minutes: int | None = None
    stated_commute_minutes: int | None = Field(None, description="Названное время дороги до вакансии интервью")
    salary_expectation: int | None = None
    team_preference: TeamPreference = TeamPreference.UNKNOWN
    important_amenities: list[Amenity] = []


class CandidateOut(BaseModel):
    id: int
    created_at: datetime
    source: CandidateSource
    vacancy_id: int | None
    profile: CandidateProfile
    transcript: str | None = None


# ---------------------------------------------------------------------------
# Вакансия
# ---------------------------------------------------------------------------


class SkillRequirement(BaseModel):
    skill: str
    min_years: float


class CertRequirement(BaseModel):
    kind: CertKind
    min_level: int | None = None


class VacancyData(BaseModel):
    title: str
    company: str
    profession: Profession
    zone: Zone
    shift: ShiftSchedule
    salary: int
    requirements: list[SkillRequirement]
    certificates: list[CertRequirement] = []
    amenities: list[Amenity] = []
    team_format: TeamFormat = TeamFormat.MIXED
    description: str = ""


class VacancyOut(VacancyData):
    id: int
    candidates_total: int = 0


# ---------------------------------------------------------------------------
# Сопоставление кандидата и вакансии
# ---------------------------------------------------------------------------


class SkillCheck(BaseModel):
    skill: str
    label: str
    required_years: float
    years: float | None
    status: CheckStatus
    note: str
    evidence: str = ""
    verified: bool = False
    evidence_status: str = ""


class CertCheck(BaseModel):
    kind: CertKind
    label: str
    required_level: int | None
    level: int | None
    status: CheckStatus
    note: str
    evidence: str = ""


class ComfortCheck(BaseModel):
    key: str
    label: str
    candidate: str
    vacancy: str
    score: float
    status: CheckStatus


class Factor(BaseModel):
    """Фактор, повлиявший на прогноз удержания (в процентных пунктах)."""

    text: str
    impact: float


class MatchReport(BaseModel):
    candidate_id: int
    full_name: str
    source: CandidateSource
    summary: str

    tech_score: float
    comfort_score: float
    retention: float
    final_score: float
    risk_level: RiskLevel
    passes_requirements: bool
    rank: int | None = None

    skill_checks: list[SkillCheck]
    cert_checks: list[CertCheck]
    comfort: list[ComfortCheck]
    risks: list[Factor]
    strengths: list[Factor]
    clarify: list[str]


class ShortlistOut(BaseModel):
    vacancy: VacancyOut
    shortlist: list[MatchReport]
    others: list[MatchReport]


class CandidateReportOut(BaseModel):
    vacancy: VacancyOut
    candidate: CandidateOut
    report: MatchReport
    shortlist_size: int


# ---------------------------------------------------------------------------
# Интервью
# ---------------------------------------------------------------------------


class InterviewMessage(BaseModel):
    role: str  # "assistant" | "candidate"
    text: str
    key: str | None = None


class InterviewOut(BaseModel):
    id: int
    vacancy_id: int
    status: str
    step: int
    total_questions: int
    messages: list[InterviewMessage]
    candidate_id: int | None = None
    error: str | None = None


class AnswerIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class InterviewCreateIn(BaseModel):
    vacancy_id: int
