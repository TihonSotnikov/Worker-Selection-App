"""
Генератор синтетических данных: кандидаты, вакансии и исходы первых 90 дней.

Все персональные данные вымышлены. Исход (остался / ушёл) задаётся скрытыми
правилами поверх признаков пары — модель должна их «переоткрыть».
Главное правило из ТЗ: кандидаты, не готовые к ночным сменам, в ночную
смену уходят примерно в 80% случаев.
"""

import math
import random
from datetime import date

from app.core.catalog import (
    CERT_HAS_LEVEL,
    MARKET_SALARY,
    PROFESSION_LABELS,
    SHIFT_PREFERENCE_LABELS,
    SKILLS,
    lower_first,
    roman,
    skills_for,
    years_ru,
)
from app.core.enums import (
    Amenity,
    CertKind,
    Profession,
    ShiftPreference,
    ShiftSchedule,
    TeamFormat,
    TeamPreference,
    Zone,
)
from app.core.schemas import (
    CandidateProfile,
    CertClaim,
    CertRequirement,
    SkillClaim,
    SkillRequirement,
    VacancyData,
)
from app.ml.feature_contract import FEATURE_COLS, build_features

MALE_NAMES = [
    "Дмитрий", "Алексей", "Сергей", "Андрей", "Максим", "Иван", "Николай", "Павел", "Евгений", "Олег",
    "Виктор", "Роман", "Артём", "Владимир", "Михаил", "Константин", "Игорь", "Денис", "Юрий", "Григорий",
]  # fmt: skip
FEMALE_NAMES = ["Ольга", "Елена", "Наталья", "Анна", "Ирина", "Светлана", "Татьяна", "Марина"]
SURNAMES = [
    "Иванов", "Кузнецов", "Смирнов", "Попов", "Волков", "Соколов", "Лебедев", "Козлов", "Новиков", "Морозов",
    "Петров", "Васильев", "Зайцев", "Павлов", "Семёнов", "Голубев", "Виноградов", "Богданов", "Воробьёв",
    "Фёдоров", "Михайлов", "Беляев", "Тарасов", "Белов", "Комаров", "Орлов", "Киселёв", "Макаров", "Андреев",
    "Ковалёв", "Ильин", "Гусев", "Титов", "Кузьмин", "Кудрявцев", "Баранов", "Куликов", "Алексеев", "Степанов",
    "Яковлев", "Сорокин", "Романов", "Захаров", "Борисов", "Королёв", "Герасимов", "Пономарёв", "Григорьев",
]  # fmt: skip
PATRONYMICS = [
    ("Сергеевич", "Сергеевна"), ("Александрович", "Александровна"), ("Николаевич", "Николаевна"),
    ("Викторович", "Викторовна"), ("Иванович", "Ивановна"), ("Петрович", "Петровна"),
    ("Андреевич", "Андреевна"), ("Михайлович", "Михайловна"), ("Юрьевич", "Юрьевна"),
    ("Владимирович", "Владимировна"),
]  # fmt: skip

# Насколько часто навык встречается у представителей профессии.
SKILL_PREVALENCE: dict[str, float] = {
    "cnc_milling": 0.6, "cnc_turning": 0.55, "fanuc": 0.65, "sinumerik": 0.35, "gcode": 0.45,
    "blueprints": 0.85, "metrology": 0.8,
    "tig": 0.6, "mig_mag": 0.75, "mma": 0.7, "stainless": 0.45,
    "equipment_repair": 0.8, "plc": 0.45, "hydraulics": 0.55, "electrical_install": 0.7, "drives": 0.4,
}  # fmt: skip

ARCHETYPES = ["strong", "average", "junior", "job_hopper", "night_averse", "far_away", "expensive"]
ARCHETYPE_WEIGHTS = [2, 4, 2, 1.5, 1.5, 1, 1]

# Состав демо-пула на одну профессию: интересный разброс для шорт-листа.
POOL_MIX = [
    "strong", "strong", "strong", "average", "average", "average", "average", "average",
    "junior", "junior", "job_hopper", "job_hopper", "night_averse", "night_averse", "far_away", "expensive",
]  # fmt: skip

FEMALE_SHARE = {Profession.CNC: 0.15, Profession.WELDER: 0.12, Profession.ELECTRO: 0.1}


def _full_name(rng: random.Random, profession: Profession) -> str:
    female = rng.random() < FEMALE_SHARE[profession]
    surname = rng.choice(SURNAMES)
    patronymic = rng.choice(PATRONYMICS)
    if female:
        return f"{surname}а {rng.choice(FEMALE_NAMES)} {patronymic[1]}"
    return f"{surname} {rng.choice(MALE_NAMES)} {patronymic[0]}"


def _round_half(x: float) -> float:
    return max(0.5, round(x * 2) / 2)


def _experience(rng: random.Random, archetype: str) -> float:
    low, high = {"strong": (6, 20), "average": (2, 9), "junior": (0.5, 2)}.get(archetype, (1.5, 12))
    return _round_half(rng.uniform(low, high))


def _skills(rng: random.Random, profession: Profession, archetype: str, experience: float) -> list[SkillClaim]:
    shift = {"strong": 0.2, "junior": -0.25}.get(archetype, 0.0)
    claims = []
    for skill in skills_for(profession):
        if rng.random() >= min(0.95, max(0.15, SKILL_PREVALENCE[skill.key] + shift)):
            continue
        low = 0.6 if archetype == "strong" else 0.25
        years = _round_half(experience * rng.uniform(low, 1.0))
        years = min(years, experience)
        verified = rng.random() > 0.08
        evidence = ""
        if verified:
            template = rng.choice(skill.evidence_templates)
            evidence = template.format(years=years_ru(years), years_cap=years_ru(years))
        claims.append(SkillClaim(skill=skill.key, years=years, evidence=evidence, verified=verified))
    if not claims:  # у любого кандидата профессии есть хотя бы один навык
        skill = rng.choice(skills_for(profession))
        years = _round_half(experience)
        evidence = rng.choice(skill.evidence_templates).format(years=years_ru(years), years_cap=years_ru(years))
        claims.append(SkillClaim(skill=skill.key, years=years, evidence=evidence, verified=True))
    return claims


def _cert_evidence(kind: CertKind, level: int | None, valid: bool) -> str:
    year = date.today().year - 1
    text = {
        CertKind.GRADE: f"{level}-й разряд, удостоверение на руках.",
        CertKind.NAKS: f"Аттестация НАКС, продлена в {year} году.",
        CertKind.ELSAFETY: f"{roman(level or 0)} группа по электробезопасности.",
        CertKind.SLINGER: "Есть удостоверение стропальщика.",
    }[kind]
    return text if valid else text.rstrip(".") + ", но срок уже истёк."


def _certificates(rng: random.Random, profession: Profession, archetype: str) -> list[CertClaim]:
    level_range = {"strong": (5, 6), "junior": (2, 3)}.get(archetype, (3, 5))
    wanted: list[tuple[CertKind, float]] = [(CertKind.SLINGER, 0.25)]
    if profession in (Profession.CNC, Profession.WELDER):
        wanted.append((CertKind.GRADE, 0.75))
    if profession == Profession.WELDER:
        wanted.append((CertKind.NAKS, {"strong": 0.8, "junior": 0.1}.get(archetype, 0.45)))
    if profession == Profession.ELECTRO:
        wanted.append((CertKind.ELSAFETY, 0.85))

    claims = []
    for kind, prob in wanted:
        if rng.random() >= prob:
            continue
        level = None
        if kind in CERT_HAS_LEVEL:
            low, high = level_range
            level = min(rng.randint(low, high), 5) if kind == CertKind.ELSAFETY else rng.randint(low, high)
        valid = rng.random() < 0.88
        claims.append(CertClaim(kind=kind, level=level, valid=valid, evidence=_cert_evidence(kind, level, valid)))
    return claims


def _summary(profile: CandidateProfile) -> str:
    top = sorted(profile.skills, key=lambda c: c.years or 0, reverse=True)[:3]
    skills = ", ".join(lower_first(SKILLS[c.skill].label) for c in top)
    shift = lower_first(SHIFT_PREFERENCE_LABELS[profile.shift_preference])
    salary = f"{profile.salary_expectation // 1000} тыс. ₽" if profile.salary_expectation else "не названы"
    return (
        f"{PROFESSION_LABELS[profile.profession]}, опыт {years_ru(profile.experience_years or 0)}. "
        f"Сильные стороны: {skills}. График: {shift}. Ожидания: {salary}."
    )


def generate_candidate(rng: random.Random, profession: Profession, archetype: str | None = None) -> CandidateProfile:
    archetype = archetype or rng.choices(ARCHETYPES, weights=ARCHETYPE_WEIGHTS)[0]
    experience = _experience(rng, archetype)

    if archetype == "night_averse":
        shift = ShiftPreference.DAY_ONLY
    else:
        shift = rng.choices(
            [ShiftPreference.DAY_ONLY, ShiftPreference.ANY, ShiftPreference.NIGHT], weights=[22, 68, 10]
        )[0]

    zone = Zone.SUBURB if archetype == "far_away" else rng.choice(list(Zone))
    has_car = rng.random() < (0.3 if archetype == "far_away" else 0.5)

    salary = MARKET_SALARY[profession] * (0.8 + 0.03 * min(experience, 12)) * rng.uniform(0.92, 1.08)
    if archetype == "expensive":
        salary *= 1.35
    salary = int(round(salary / 5000) * 5000)

    amenities_pool = [Amenity.CANTEEN, Amenity.SHOWER, Amenity.SHUTTLE, Amenity.DORMITORY]
    amenity_weights = [0.5, 0.35, 0.3, 0.12] if archetype != "far_away" else [0.4, 0.3, 0.7, 0.4]
    amenities = [a for a, w in zip(amenities_pool, amenity_weights, strict=True) if rng.random() < w][:2]

    if archetype == "job_hopper":
        turnovers = rng.randint(4, 6)
    elif archetype == "strong":
        turnovers = rng.choices([0, 1], weights=[3, 2])[0]
    else:
        turnovers = rng.choices([0, 1, 2, 3], weights=[3, 4, 2, 1])[0]

    profile = CandidateProfile(
        full_name=_full_name(rng, profession),
        profession=profession,
        experience_years=experience,
        previous_turnovers=turnovers,
        skills=_skills(rng, profession, archetype, experience),
        certificates=_certificates(rng, profession, archetype),
        shift_preference=shift,
        home_zone=zone,
        has_car=has_car,
        max_commute_minutes=rng.choice([40, 45, 50, 60, 60, 75, 90]),
        salary_expectation=salary,
        team_preference=rng.choices(
            [TeamPreference.TEAM, TeamPreference.ANY, TeamPreference.SOLO], weights=[35, 45, 20]
        )[0],
        important_amenities=amenities,
    )
    profile.summary = _summary(profile)
    return profile


def generate_pool(rng: random.Random, profession: Profession) -> list[CandidateProfile]:
    return [generate_candidate(rng, profession, archetype) for archetype in POOL_MIX]


def generate_vacancy(rng: random.Random, profession: Profession) -> VacancyData:
    """Случайная вакансия — только для обучающей выборки."""

    skills = skills_for(profession)
    weights = [SKILL_PREVALENCE[s.key] for s in skills]
    target = rng.randint(2, 3)
    picked: list[str] = []
    while len(picked) < target:
        key = rng.choices(skills, weights=weights)[0].key
        if key not in picked:
            picked.append(key)

    certs = []
    if profession in (Profession.CNC, Profession.WELDER) and rng.random() < 0.5:
        certs.append(CertRequirement(kind=CertKind.GRADE, min_level=rng.randint(3, 5)))
    if profession == Profession.WELDER and rng.random() < 0.5:
        certs.append(CertRequirement(kind=CertKind.NAKS))
    if profession == Profession.ELECTRO and rng.random() < 0.8:
        certs.append(CertRequirement(kind=CertKind.ELSAFETY, min_level=3))

    amenity_probs = {Amenity.CANTEEN: 0.6, Amenity.SHOWER: 0.6, Amenity.SHUTTLE: 0.4, Amenity.DORMITORY: 0.2}
    return VacancyData(
        title=PROFESSION_LABELS[profession],
        company="Синтетика",
        profession=profession,
        zone=rng.choice(list(Zone)),
        shift=rng.choices(list(ShiftSchedule), weights=[45, 20, 35])[0],
        salary=int(round(MARKET_SALARY[profession] * rng.uniform(0.8, 1.3) / 5000) * 5000),
        requirements=[SkillRequirement(skill=key, min_years=rng.choice([1, 2, 3, 3, 4, 5])) for key in picked],
        certificates=certs,
        amenities=[a for a, p in amenity_probs.items() if rng.random() < p],
        team_format=rng.choice(list(TeamFormat)),
    )


def retention_logit(f: dict[str, float]) -> float:
    """Скрытые правила удержания («истина» симуляции), в логитах."""

    logit = 1.4
    logit -= {0: 0.0, 1: 1.2, 2: 2.8}[int(f["shift_conflict"])]

    commute = f["commute_minutes"]
    if commute > 100:
        logit -= 1.6
    elif commute > 75:
        logit -= 0.9
    elif commute > 50:
        logit -= 0.3
    elif commute <= 30:
        logit += 0.3
    logit -= 0.025 * f["commute_excess"]

    gap = f["salary_gap_pct"]
    if gap < -0.2:
        logit -= 1.6
    elif gap < -0.08:
        logit -= 0.7
    elif gap > 0.1:
        logit += 0.4

    turnovers = f["previous_turnovers"]
    if turnovers >= 4:
        logit -= 1.8
    elif turnovers >= 2:
        logit -= 0.6
    elif turnovers == 0:
        logit += 0.4

    coverage = f["skill_coverage"]
    if coverage < 0.5:
        logit -= 1.0
    elif coverage < 0.8:
        logit -= 0.4
    elif coverage >= 0.95:
        logit += 0.3

    logit -= 0.35 * f["amenities_missing"]
    logit -= 0.6 * f["team_mismatch"]

    experience = f["experience_years"]
    if experience < 1:
        logit -= 0.6
    elif experience >= 8:
        logit += 0.3
    return logit


def simulate_outcome(features: dict[str, float], rng: random.Random) -> int:
    """1 — сотрудник остался после 90 дней, 0 — ушёл."""

    p = 1 / (1 + math.exp(-(retention_logit(features) + rng.gauss(0, 0.3))))
    return int(rng.random() < p)


def generate_training_data(rows: int, seed: int) -> tuple[list[list[float]], list[int]]:
    rng = random.Random(seed)
    x, y = [], []
    for _ in range(rows):
        profession = rng.choice(list(Profession))
        candidate = generate_candidate(rng, profession)
        vacancy = generate_vacancy(rng, profession)
        features, _ = build_features(candidate, vacancy)
        x.append([float(features[col]) for col in FEATURE_COLS])
        y.append(simulate_outcome(features, rng))
    return x, y
