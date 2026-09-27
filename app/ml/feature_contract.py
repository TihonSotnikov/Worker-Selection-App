"""
Контракт признаков модели удержания.

Признаки считаются для ПАРЫ «кандидат × вакансия»: одинаковый кандидат может
хорошо подходить на дневную вакансию рядом с домом и плохо — на ночную
на другом конце города. Здесь же живут функции оценки навыков и удостоверений,
чтобы ML и отчёт для рекрутера считали их одинаково.

Намеренно НЕ используются возраст, пол, семейное положение и подобные
признаки: по ст. 64 ТК РФ отказ по ним — дискриминация. Модель смотрит только
на то, что относится к работе и условиям.
"""

from dataclasses import dataclass, field

from app.core.catalog import travel_minutes, years_from_ru, years_ru
from app.core.enums import (
    Amenity,
    CheckStatus,
    ShiftPreference,
    ShiftSchedule,
    TeamFormat,
    TeamPreference,
)
from app.core.schemas import (
    CandidateProfile,
    CertClaim,
    CertRequirement,
    SkillClaim,
    SkillRequirement,
    VacancyData,
)

FEATURE_COLS: list[str] = [
    "experience_years",
    "previous_turnovers",
    "skill_coverage",
    "shift_conflict",
    "commute_minutes",
    "commute_excess",
    "salary_gap_pct",
    "amenities_missing",
    "team_mismatch",
]

# Монотонность: +1 — чем больше, тем выше удержание; -1 — наоборот.
MONOTONE: dict[str, int] = {
    "experience_years": 1,
    "previous_turnovers": -1,
    "skill_coverage": 1,
    "shift_conflict": -1,
    "commute_minutes": -1,
    "commute_excess": -1,
    "salary_gap_pct": 1,
    "amenities_missing": -1,
    "team_mismatch": -1,
}

# Нейтральные значения для того, что не удалось выяснить на интервью.
DEFAULT_EXPERIENCE = 3.0
DEFAULT_TURNOVERS = 1
DEFAULT_COMMUTE = 45
DEFAULT_MAX_COMMUTE = 60


@dataclass
class Assessment:
    status: CheckStatus
    score: float
    note: str


@dataclass
class PairContext:
    """Промежуточные значения, из которых собраны признаки — нужны для объяснений."""

    skill_assessments: list[Assessment]
    cert_assessments: list[Assessment]
    skill_coverage: float
    shift_conflict: int
    commute_minutes: int | None
    commute_source: str  # stated | zones | unknown
    max_commute: int | None
    salary_gap_pct: float | None
    missing_amenities: list[Amenity] = field(default_factory=list)
    team_mismatch: bool = False


def assess_skill(claim: SkillClaim | None, req: SkillRequirement) -> Assessment:
    need = f"нужно {years_from_ru(req.min_years)}"
    if claim is None:
        return Assessment(CheckStatus.MISSING, 0.0, f"Не подтверждён, {need}")
    # LLM заявила навык, но подтверждения в ответах нет — считаем, что навыка не подтверждали.
    if claim.evidence_status == "off_topic":
        return Assessment(CheckStatus.MISSING, 0.0, f"Цитата не подтверждает навык, {need}")
    if claim.evidence_status == "not_found":
        return Assessment(CheckStatus.MISSING, 0.0, f"Цитаты нет в ответах кандидата, {need}")
    if claim.years is None:
        return Assessment(CheckStatus.PARTIAL, 0.5, f"Навык назван, стаж не уточнён ({need})")
    if claim.years >= req.min_years:
        if claim.verified:
            return Assessment(CheckStatus.OK, 1.0, f"{years_ru(claim.years)}, {need}")
        return Assessment(CheckStatus.PARTIAL, 0.7, f"{years_ru(claim.years)}, но без подтверждения в ответах")
    score = round(max(0.2, min(0.8, claim.years / req.min_years * 0.8)), 2)
    return Assessment(CheckStatus.PARTIAL, score, f"{years_ru(claim.years)}, {need}")


def assess_cert(claim: CertClaim | None, req: CertRequirement) -> Assessment:
    if claim is None:
        return Assessment(CheckStatus.MISSING, 0.0, "Нет")
    if not claim.valid:
        return Assessment(CheckStatus.PARTIAL, 0.5, "Срок действия истёк")
    if req.min_level:
        if claim.level is None:
            return Assessment(CheckStatus.PARTIAL, 0.6, f"Уровень не назван, нужен от {req.min_level}")
        if claim.level < req.min_level:
            return Assessment(CheckStatus.PARTIAL, 0.4, f"Уровень {claim.level}, нужен от {req.min_level}")
        return Assessment(CheckStatus.OK, 1.0, f"Уровень {claim.level}, нужен от {req.min_level}")
    return Assessment(CheckStatus.OK, 1.0, "Есть")


def shift_conflict(pref: ShiftPreference, schedule: ShiftSchedule) -> int:
    """0 — нет конфликта, 1 — частичный, 2 — полный (дневной человек на ночной вакансии)."""

    if pref == ShiftPreference.DAY_ONLY:
        return {ShiftSchedule.DAY: 0, ShiftSchedule.ROTATING: 1, ShiftSchedule.NIGHT: 2}[schedule]
    if pref == ShiftPreference.NIGHT and schedule == ShiftSchedule.DAY:
        return 1
    return 0


def team_mismatch(pref: TeamPreference, fmt: TeamFormat) -> bool:
    return (pref == TeamPreference.SOLO and fmt == TeamFormat.TEAM) or (
        pref == TeamPreference.TEAM and fmt == TeamFormat.SOLO
    )


def commute_for(profile: CandidateProfile, vacancy: VacancyData, stated_applies: bool) -> tuple[int | None, str]:
    if stated_applies and profile.stated_commute_minutes is not None:
        return profile.stated_commute_minutes, "stated"
    if profile.home_zone is not None:
        return travel_minutes(profile.home_zone, vacancy.zone, bool(profile.has_car)), "zones"
    return None, "unknown"


def build_features(
    profile: CandidateProfile, vacancy: VacancyData, stated_applies: bool = False
) -> tuple[dict[str, float], PairContext]:
    """
    Собирает признаки пары кандидат × вакансия.

    Parameters
    ----------
    stated_applies : bool
        Кандидат проходил интервью именно на эту вакансию, поэтому названное им
        время дороги относится к ней и важнее расчёта по районам.
    """

    claims = {c.skill: c for c in profile.skills}
    skill_assessments = [assess_skill(claims.get(req.skill), req) for req in vacancy.requirements]
    coverage = sum(a.score for a in skill_assessments) / len(skill_assessments) if skill_assessments else 1.0

    certs = {c.kind: c for c in profile.certificates}
    cert_assessments = [assess_cert(certs.get(req.kind), req) for req in vacancy.certificates]

    commute, commute_source = commute_for(profile, vacancy, stated_applies)
    commute_value = commute if commute is not None else DEFAULT_COMMUTE
    max_commute = profile.max_commute_minutes if profile.max_commute_minutes is not None else DEFAULT_MAX_COMMUTE

    gap = None
    if profile.salary_expectation:
        gap = (vacancy.salary - profile.salary_expectation) / profile.salary_expectation

    missing = [a for a in profile.important_amenities if a not in vacancy.amenities]
    conflict = shift_conflict(profile.shift_preference, vacancy.shift)
    mismatch = team_mismatch(profile.team_preference, vacancy.team_format)

    features = {
        "experience_years": profile.experience_years if profile.experience_years is not None else DEFAULT_EXPERIENCE,
        "previous_turnovers": profile.previous_turnovers
        if profile.previous_turnovers is not None
        else DEFAULT_TURNOVERS,
        "skill_coverage": round(coverage, 3),
        "shift_conflict": conflict,
        "commute_minutes": commute_value,
        "commute_excess": max(0, commute_value - max_commute),
        "salary_gap_pct": round(gap, 3) if gap is not None else 0.0,
        "amenities_missing": len(missing),
        "team_mismatch": int(mismatch),
    }
    context = PairContext(
        skill_assessments=skill_assessments,
        cert_assessments=cert_assessments,
        skill_coverage=coverage,
        shift_conflict=conflict,
        commute_minutes=commute,
        commute_source=commute_source,
        max_commute=profile.max_commute_minutes,
        salary_gap_pct=gap,
        missing_amenities=missing,
        team_mismatch=mismatch,
    )
    return features, context
