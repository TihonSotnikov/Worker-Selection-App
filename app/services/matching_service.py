"""
Сопоставление кандидатов и вакансий по двум осям + прогноз удержания.

- Ось «Навыки»: подтверждённые навыки со стажем и удостоверения.
- Ось «Комфорт»: смены, дорога, зарплата, бытовые условия, формат работы.
- Удержание: вероятность проработать 90 дней (CatBoost), с объяснением.

Итоговый балл = 40% навыки + 25% комфорт + 35% удержание. В шорт-лист попадают
только кандидаты, у которых подтверждены все обязательные навыки.
"""

from app.core.catalog import (
    AMENITY_LABELS,
    CERT_LABELS,
    SHIFT_PREFERENCE_LABELS,
    SHIFT_SCHEDULE_LABELS,
    SKILLS,
    TEAM_FORMAT_LABELS,
    TEAM_PREFERENCE_LABELS,
    ZONE_LABELS,
    years_ru,
)
from app.core.enums import CheckStatus, RiskLevel, ShiftPreference, TeamPreference
from app.core.schemas import (
    CandidateOut,
    CandidateProfile,
    CertCheck,
    ComfortCheck,
    Factor,
    MatchReport,
    ShortlistOut,
    SkillCheck,
    VacancyOut,
)
from app.ml.feature_contract import PairContext, build_features
from app.ml.predictor import RetentionModel

SHORTLIST_SIZE = 5
WEIGHTS = {"tech": 0.40, "comfort": 0.25, "retention": 0.35}
COMFORT_WEIGHTS = {"shift": 0.30, "commute": 0.25, "salary": 0.25, "amenities": 0.10, "team": 0.10}
SKILLS_SHARE_IN_TECH = 0.75
MIN_IMPACT_PP = 2.0

# Признаки, которые в объяснениях показываются одним фактором.
FACTOR_GROUPS = {"commute_minutes": "commute", "commute_excess": "commute"}


def _risk_level(retention: float) -> RiskLevel:
    if retention >= 0.65:
        return RiskLevel.LOW
    if retention >= 0.4:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def _money(value: int) -> str:
    return f"{value:,} ₽".replace(",", " ")


# ---------------------------------------------------------------------------
# Ось «Навыки»
# ---------------------------------------------------------------------------


def _skill_checks(profile: CandidateProfile, vacancy: VacancyOut, ctx: PairContext) -> list[SkillCheck]:
    claims = {c.skill: c for c in profile.skills}
    checks = []
    for req, assessment in zip(vacancy.requirements, ctx.skill_assessments, strict=True):
        claim = claims.get(req.skill)
        checks.append(
            SkillCheck(
                skill=req.skill,
                label=SKILLS[req.skill].label,
                required_years=req.min_years,
                years=claim.years if claim else None,
                status=assessment.status,
                note=assessment.note,
                evidence=claim.evidence if claim else "",
                verified=bool(claim and claim.verified),
                evidence_status=claim.evidence_status if claim else "",
            )
        )
    return checks


def _cert_checks(profile: CandidateProfile, vacancy: VacancyOut, ctx: PairContext) -> list[CertCheck]:
    claims = {c.kind: c for c in profile.certificates}
    checks = []
    for req, assessment in zip(vacancy.certificates, ctx.cert_assessments, strict=True):
        claim = claims.get(req.kind)
        checks.append(
            CertCheck(
                kind=req.kind,
                label=CERT_LABELS[req.kind],
                required_level=req.min_level,
                level=claim.level if claim else None,
                status=assessment.status,
                note=assessment.note,
                evidence=claim.evidence if claim else "",
            )
        )
    return checks


def _tech_score(ctx: PairContext) -> float:
    if not ctx.cert_assessments:
        return 100 * ctx.skill_coverage
    certs = sum(a.score for a in ctx.cert_assessments) / len(ctx.cert_assessments)
    return 100 * (SKILLS_SHARE_IN_TECH * ctx.skill_coverage + (1 - SKILLS_SHARE_IN_TECH) * certs)


# ---------------------------------------------------------------------------
# Ось «Комфорт»
# ---------------------------------------------------------------------------


def _comfort_checks(profile: CandidateProfile, vacancy: VacancyOut, ctx: PairContext) -> list[ComfortCheck]:
    checks = []

    pref = profile.shift_preference
    if pref == ShiftPreference.UNKNOWN:
        shift_score, shift_status = 0.6, CheckStatus.UNKNOWN
    else:
        shift_score, shift_status = {
            0: (1.0, CheckStatus.OK),
            1: (0.4, CheckStatus.PARTIAL),
            2: (0.0, CheckStatus.MISSING),
        }[ctx.shift_conflict]
    checks.append(
        ComfortCheck(
            key="shift",
            label="График",
            candidate=SHIFT_PREFERENCE_LABELS[pref],
            vacancy=SHIFT_SCHEDULE_LABELS[vacancy.shift],
            score=shift_score,
            status=shift_status,
        )
    )

    minutes, limit = ctx.commute_minutes, ctx.max_commute
    if minutes is None:
        commute_text, commute_score, commute_status = "Не выяснено", 0.6, CheckStatus.UNKNOWN
    else:
        commute_text = f"~{minutes} мин" + (" (со слов кандидата)" if ctx.commute_source == "stated" else "")
        if limit is not None:
            commute_text += f", готов тратить до {limit} мин"
        effective_limit = limit if limit is not None else 60
        if minutes <= effective_limit:
            commute_score, commute_status = 1.0, CheckStatus.OK
        else:
            commute_score = max(0.0, 1 - (minutes - effective_limit) / 60)
            commute_status = CheckStatus.PARTIAL if commute_score > 0.3 else CheckStatus.MISSING
    checks.append(
        ComfortCheck(
            key="commute",
            label="Дорога",
            candidate=commute_text,
            vacancy=ZONE_LABELS[vacancy.zone],
            score=commute_score,
            status=commute_status,
        )
    )

    gap = ctx.salary_gap_pct
    if gap is None:
        salary_text, salary_score, salary_status = "Не названы", 0.6, CheckStatus.UNKNOWN
    else:
        salary_text = _money(profile.salary_expectation or 0)
        salary_score = 1.0 if gap >= 0 else max(0.0, 1 + gap / 0.25)
        salary_status = (
            CheckStatus.OK if gap >= -0.03 else CheckStatus.PARTIAL if salary_score > 0.3 else CheckStatus.MISSING
        )
    checks.append(
        ComfortCheck(
            key="salary",
            label="Зарплата",
            candidate=salary_text,
            vacancy=_money(vacancy.salary),
            score=salary_score,
            status=salary_status,
        )
    )

    important = profile.important_amenities
    if not important:
        amen_score, amen_status = 1.0, CheckStatus.OK
    else:
        amen_score = 1 - len(ctx.missing_amenities) / len(important)
        amen_status = (
            CheckStatus.OK
            if not ctx.missing_amenities
            else CheckStatus.PARTIAL
            if amen_score > 0
            else CheckStatus.MISSING
        )
    checks.append(
        ComfortCheck(
            key="amenities",
            label="Бытовые условия",
            candidate=", ".join(AMENITY_LABELS[a] for a in important) or "Не критичны",
            vacancy=", ".join(AMENITY_LABELS[a] for a in vacancy.amenities) or "—",
            score=amen_score,
            status=amen_status,
        )
    )

    team_pref = profile.team_preference
    if team_pref == TeamPreference.UNKNOWN:
        team_score, team_status = 0.8, CheckStatus.UNKNOWN
    elif ctx.team_mismatch:
        team_score, team_status = 0.4, CheckStatus.PARTIAL
    else:
        team_score, team_status = 1.0, CheckStatus.OK
    checks.append(
        ComfortCheck(
            key="team",
            label="Формат работы",
            candidate=TEAM_PREFERENCE_LABELS[team_pref],
            vacancy=TEAM_FORMAT_LABELS[vacancy.team_format],
            score=team_score,
            status=team_status,
        )
    )
    for check in checks:
        check.score = round(check.score, 2)
    return checks


def _comfort_score(checks: list[ComfortCheck]) -> float:
    return 100 * sum(COMFORT_WEIGHTS[c.key] * c.score for c in checks)


# ---------------------------------------------------------------------------
# Объяснение прогноза удержания
# ---------------------------------------------------------------------------


def _factor_text(
    group: str, positive: bool, features: dict, profile: CandidateProfile, vacancy: VacancyOut, ctx: PairContext
) -> str | None:
    if group == "shift_conflict":
        if not positive:
            if ctx.shift_conflict == 2:
                return "Ночные смены, а кандидат готов работать только днём"
            if profile.shift_preference == ShiftPreference.DAY_ONLY:
                return "В графике есть ночные смены, а кандидат хочет только дневные"
            if profile.shift_preference == ShiftPreference.NIGHT:
                return "Кандидат предпочитает ночные смены, а здесь только дневные"
            return None
        if profile.shift_preference == ShiftPreference.UNKNOWN:
            return None
        return "График вакансии устраивает кандидата"

    if group == "commute":
        if ctx.commute_minutes is None:
            return None
        minutes = ctx.commute_minutes
        excess = int(features["commute_excess"])
        if not positive:
            if excess > 0 and ctx.max_commute is not None:
                return f"Дорога ~{minutes} мин — на {excess} мин дольше, чем кандидат готов тратить"
            return f"Дорога до работы ~{minutes} мин в одну сторону"
        if minutes <= 30:
            return f"Дорога до работы всего ~{minutes} мин"
        return f"Дорога до работы ~{minutes} мин — в пределах привычного"

    if group == "salary_gap_pct":
        gap = ctx.salary_gap_pct
        if gap is None:
            return None
        if not positive:
            return f"Зарплата на {abs(gap) * 100:.0f}% ниже ожиданий кандидата" if gap < 0 else None
        if gap > 0.05:
            return f"Зарплата на {gap * 100:.0f}% выше ожиданий кандидата"
        return "Зарплата соответствует ожиданиям кандидата"

    if group == "previous_turnovers":
        n = profile.previous_turnovers
        if n is None:
            return None
        if not positive:
            return f"Частая смена работы: {n} за последние 5 лет" if n >= 2 else None
        return "Без смены работы за последние 5 лет" if n == 0 else "Стабильная история: одна смена работы за 5 лет"

    if group == "skill_coverage":
        coverage = ctx.skill_coverage
        if not positive:
            return f"Навыки закрывают требования только на {coverage * 100:.0f}%"
        if coverage >= 0.95:
            return "Навыки полностью закрывают требования вакансии"
        return None

    if group == "amenities_missing":
        if not profile.important_amenities:
            return None
        if not positive:
            if not ctx.missing_amenities:
                return None
            missing = ", ".join(AMENITY_LABELS[a].lower() for a in ctx.missing_amenities)
            return f"Нет важных для кандидата условий: {missing}"
        return "Есть все важные для кандидата бытовые условия" if not ctx.missing_amenities else None

    if group == "team_mismatch":
        if not positive:
            if profile.team_preference == TeamPreference.SOLO:
                return "Кандидат предпочитает работать один, а здесь бригада"
            if profile.team_preference == TeamPreference.TEAM:
                return "Кандидат хочет работать в бригаде, а здесь самостоятельная работа"
            return None
        if profile.team_preference == TeamPreference.UNKNOWN:
            return None
        return "Формат работы подходит кандидату"

    if group == "experience_years":
        if profile.experience_years is None:
            return None
        text = years_ru(profile.experience_years)
        return f"Опыт по специальности {text}" if positive else f"Небольшой опыт: {text}"
    return None


def _factors(
    impacts: dict[str, float], features: dict, profile: CandidateProfile, vacancy: VacancyOut, ctx: PairContext
) -> tuple[list[Factor], list[Factor]]:
    grouped: dict[str, float] = {}
    for feature, impact in impacts.items():
        group = FACTOR_GROUPS.get(feature, feature)
        grouped[group] = grouped.get(group, 0.0) + impact

    risks, strengths = [], []
    for group, impact in grouped.items():
        if abs(impact) < MIN_IMPACT_PP:
            continue
        text = _factor_text(group, impact > 0, features, profile, vacancy, ctx)
        if text:
            (strengths if impact > 0 else risks).append(Factor(text=text, impact=round(impact, 1)))
    risks.sort(key=lambda f: f.impact)
    strengths.sort(key=lambda f: -f.impact)
    return risks[:4], strengths[:4]


def _clarify(profile: CandidateProfile, ctx: PairContext, skill_checks: list[SkillCheck]) -> list[str]:
    items = []
    if profile.shift_preference == ShiftPreference.UNKNOWN:
        items.append("Отношение к ночным сменам")
    if ctx.commute_minutes is None:
        items.append("Откуда кандидат будет добираться и сколько времени займёт дорога")
    if profile.salary_expectation is None:
        items.append("Зарплатные ожидания")
    if profile.previous_turnovers is None:
        items.append("Сколько мест работы сменил кандидат за последние 5 лет")
    if profile.team_preference == TeamPreference.UNKNOWN:
        items.append("Предпочтения по формату работы: бригада или самостоятельно")
    for check in skill_checks:
        if check.status == CheckStatus.MISSING:
            items.append(f"Навык «{check.label}» — на интервью не подтверждён")
        elif check.years is None:
            items.append(f"Стаж по навыку «{check.label}»")
    return items


# ---------------------------------------------------------------------------
# Отчёты и шорт-лист
# ---------------------------------------------------------------------------


def build_reports(model: RetentionModel, vacancy: VacancyOut, candidates: list[CandidateOut]) -> list[MatchReport]:
    """Отчёты по всем кандидатам вакансии, отсортированные для шорт-листа."""

    pairs = [build_features(c.profile, vacancy, stated_applies=c.vacancy_id == vacancy.id) for c in candidates]
    features = [p[0] for p in pairs]
    retentions = model.predict(features)
    impacts = model.explain(features)

    reports = []
    for candidate, (feats, ctx), retention, impact in zip(candidates, pairs, retentions, impacts, strict=True):
        profile = candidate.profile
        skill_checks = _skill_checks(profile, vacancy, ctx)
        comfort = _comfort_checks(profile, vacancy, ctx)
        tech, comfort_score = _tech_score(ctx), _comfort_score(comfort)
        final = WEIGHTS["tech"] * tech + WEIGHTS["comfort"] * comfort_score + WEIGHTS["retention"] * retention * 100
        risks, strengths = _factors(impact, feats, profile, vacancy, ctx)
        reports.append(
            MatchReport(
                candidate_id=candidate.id,
                full_name=profile.full_name,
                source=candidate.source,
                summary=profile.summary,
                tech_score=round(tech, 1),
                comfort_score=round(comfort_score, 1),
                retention=round(retention, 3),
                final_score=round(final, 1),
                risk_level=_risk_level(retention),
                passes_requirements=all(c.status != CheckStatus.MISSING for c in skill_checks),
                skill_checks=skill_checks,
                cert_checks=_cert_checks(profile, vacancy, ctx),
                comfort=comfort,
                risks=risks,
                strengths=strengths,
                clarify=_clarify(profile, ctx, skill_checks),
            )
        )

    reports.sort(key=lambda r: (not r.passes_requirements, -r.final_score))
    rank = 0
    for report in reports:
        if report.passes_requirements:
            rank += 1
            report.rank = rank
    return reports


def shortlist(
    model: RetentionModel, vacancy: VacancyOut, candidates: list[CandidateOut], size: int = SHORTLIST_SIZE
) -> ShortlistOut:
    reports = build_reports(model, vacancy, candidates)
    top = [r for r in reports if r.passes_requirements][:size]
    top_ids = {r.candidate_id for r in top}
    return ShortlistOut(vacancy=vacancy, shortlist=top, others=[r for r in reports if r.candidate_id not in top_ids])
