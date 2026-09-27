"""
Извлечение профиля кандидата из расшифровки интервью с помощью LLM.

1. LLM получает расшифровку и JSON-схему, в которой перечислены допустимые
   навыки, районы и значения — выдумать «новый» навык она не может.
2. Каждая цитата-подтверждение сверяется с ответами кандидата: навык считается
   подтверждённым, только если цитата действительно там есть.
"""

import re
from typing import Any

from app.ai.llm import OllamaClient
from app.core.catalog import AMENITY_LABELS, PROFESSION_LABELS, SKILLS, ZONE_LABELS, skills_for
from app.core.enums import (
    Amenity,
    CertKind,
    Profession,
    ShiftPreference,
    TeamPreference,
    Zone,
)
from app.core.schemas import CandidateProfile, CertClaim, SkillClaim, VacancyData

CANDIDATE_PREFIXES = ("кандидат:", "кандидатка:", "соискатель:")
ROLE_LINE = re.compile(r"^\s*([А-Яа-яA-Za-z\- ]{2,20}):", re.MULTILINE)


def _nullable(kind: str) -> dict[str, Any]:
    return {"type": [kind, "null"]}


def extraction_schema(profession: Profession) -> dict[str, Any]:
    skill_keys = [s.key for s in skills_for(profession)]
    properties: dict[str, Any] = {
        "full_name": {"type": "string"},
        "experience_years": _nullable("number"),
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string", "enum": skill_keys},
                    "years": _nullable("number"),
                    "evidence": {"type": "string"},
                },
                "required": ["skill", "years", "evidence"],
            },
        },
        "certificates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": [k.value for k in CertKind]},
                    "level": _nullable("integer"),
                    "valid": {"type": "boolean"},
                    "evidence": {"type": "string"},
                },
                "required": ["kind", "level", "valid", "evidence"],
            },
        },
        "shift_preference": {"type": "string", "enum": [p.value for p in ShiftPreference]},
        "home_zone": {"type": "string", "enum": [z.value for z in Zone] + ["unknown"]},
        "has_car": _nullable("boolean"),
        "stated_commute_minutes": _nullable("integer"),
        "max_commute_minutes": _nullable("integer"),
        "salary_expectation": _nullable("integer"),
        "team_preference": {"type": "string", "enum": [p.value for p in TeamPreference]},
        "important_amenities": {"type": "array", "items": {"type": "string", "enum": [a.value for a in Amenity]}},
        "previous_turnovers": _nullable("integer"),
        "summary": {"type": "string"},
    }
    return {"type": "object", "properties": properties, "required": list(properties)}


SYSTEM_PROMPT = """Ты — HR-аналитик машиностроительного завода. Тебе дают расшифровку интервью \
с кандидатом. Извлеки факты СТРОГО из слов кандидата и верни JSON по схеме.

Общие правила:
- Используй только то, что сказал кандидат. Ничего не додумывай.
- Если факт не обсуждался — null, "unknown" или пустой список.
- evidence — короткая ДОСЛОВНАЯ цитата из ответа кандидата (5–20 слов), без пересказа.

Поля:
- full_name — имя кандидата, как к нему обращался рекрутер или как он представился. Если имени нет — "Кандидат".
- experience_years — общий стаж по специальности в годах (сложи стаж на всех местах, если он назван).
- skills — только навыки из списка ниже, о которых кандидат говорит прямо. Не выводи навыки из общих слов \
(«универсал», «электрик», «всё умею»). evidence должна называть сам навык: станок, стойку, вид сварки, \
оборудование. years — стаж именно по этому навыку. Если кандидат говорит «последние 4 года на фрезерной \
группе, в основном стойки Fanuc» — это 4 года и для фрезерной обработки, и для Fanuc. Если стаж не назван — null.
- certificates — только удостоверения, которые у кандидата ЕСТЬ или были: grade — квалификационный разряд \
(«5-й разряд» → level 5; разряд часто называют вскользь, в рассказе об опыте — его тоже включай); \
naks — аттестация НАКС; elsafety — группа допуска по электробезопасности \
(«2-я группа» → level 2; если называет несколько — самая высокая); slinger — удостоверение стропальщика. \
valid = false, если срок истёк, «просрочено», «было когда-то». Если кандидат говорит, что удостоверения \
нет или он только готов его получить, — НЕ включай его.
- shift_preference: day_only — хочет только дневные смены или против ночных; any — готов к любым сменам, \
включая ночные; night — предпочитает ночные; unknown — не обсуждали.
- home_zone — район проживания, только если он совпадает с районом из списка ниже. suburb — только если \
кандидат живёт за городом (в области, в другом населённом пункте). Район не из списка или «соседний район» — unknown.
- has_car — есть ли личная машина.
- stated_commute_minutes — сколько МИНУТ, со слов кандидата, займёт дорога до ЭТОЙ работы в одну сторону. \
Диапазон — бери верхнюю границу; «час» = 60, «два с половиной часа» = 150. Километры — это не минуты: \
«живу в 100 км» без времени в пути → null. Если кандидат собирается снять жильё рядом с работой — 20.
- max_commute_minutes — сколько максимум кандидат готов тратить на дорогу, только если он это сказал.
- salary_expectation — ожидаемая зарплата на руки, рублей в месяц («сто двадцать» → 120000).
- team_preference: team — любит работать в бригаде; solo — предпочитает работать один; any — без разницы; \
unknown — не обсуждали.
- important_amenities — бытовые условия, которые кандидат назвал важными: canteen — столовая, shower — душ, \
dormitory — общежитие или жильё, shuttle — развозка или служебный транспорт.
- previous_turnovers — сколько раз кандидат сменил место работы за последние 5 лет. Оцени по рассказу \
(«нигде больше полугода не задерживался» ≈ 5).
- summary — 2–3 предложения по-русски: кто кандидат, сильные стороны, главные риски."""


def _user_prompt(transcript: str, vacancy: VacancyData) -> str:
    skills = "\n".join(f"- {s.key}: {s.label}" for s in skills_for(vacancy.profession))
    zones = "\n".join(f"- {z.value}: {label}" for z, label in ZONE_LABELS.items())
    amenities = ", ".join(f"{a.value} ({label.lower()})" for a, label in AMENITY_LABELS.items())
    required = ", ".join(SKILLS[r.skill].label for r in vacancy.requirements)
    return (
        f"Вакансия: {vacancy.title} ({PROFESSION_LABELS[vacancy.profession]}), район: {ZONE_LABELS[vacancy.zone]}.\n"
        f"Обязательные навыки: {required}.\n\n"
        f"Допустимые навыки:\n{skills}\n\nРайоны:\n{zones}\n\nБытовые условия: {amenities}.\n\n"
        f"Расшифровка интервью:\n{transcript.strip()}"
    )


# ---------------------------------------------------------------------------
# Проверка цитат
# ---------------------------------------------------------------------------


def _tokens(text: str) -> list[str]:
    text = text.lower().replace("ё", "е")
    return [t for t in re.findall(r"[a-zа-я0-9]+", text) if len(t) >= 3 or t.isdigit()]


def candidate_speech(transcript: str) -> str:
    """Реплики кандидата. Если ролей в тексте нет (например, аудио) — весь текст."""

    if not ROLE_LINE.search(transcript):
        return transcript
    lines, current_is_candidate = [], False
    for line in transcript.splitlines():
        role = ROLE_LINE.match(line)
        if role:
            current_is_candidate = line.strip().lower().startswith(CANDIDATE_PREFIXES)
            line = line[role.end() :]
        if current_is_candidate:
            lines.append(line)
    return "\n".join(lines) or transcript


def mentions_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = text.lower().replace("ё", "е")
    return any(k in normalized for k in keywords)


GRADE_RE = re.compile(r"(\d)\s*-?\s*(?:й|ый|ой|ий)?\s+разряд|разряд\w*\s+(\d)", re.IGNORECASE)
EXPIRED_RE = re.compile(r"просроч|истек|истёк|закончил", re.IGNORECASE)


def grade_from_speech(speech: str) -> CertClaim | None:
    """Страховка: разряд, названный вскользь, маленькая модель иногда пропускает."""

    for sentence in re.split(r"(?<=[.!?])\s+", speech):
        match = GRADE_RE.search(sentence)
        if match:
            level = int(match.group(1) or match.group(2))
            valid = not EXPIRED_RE.search(sentence)
            return CertClaim(kind=CertKind.GRADE, level=level, valid=valid, evidence=sentence.strip())
    return None


NEGATION = re.compile(r"\b(нет|не имею|отсутству|не получал)", re.IGNORECASE)


def quote_found(quote: str, speech: str, threshold: float = 0.75) -> bool:
    """Цитата считается найденной, если ≥75% её слов встречаются в речи кандидата."""

    quote_tokens = _tokens(quote)
    if len(quote_tokens) < 2:
        return False
    speech_tokens = set(_tokens(speech))
    found = sum(1 for t in quote_tokens if t in speech_tokens)
    return found / len(quote_tokens) >= threshold


# ---------------------------------------------------------------------------
# Сборка профиля
# ---------------------------------------------------------------------------


def _clamp(value: float | int | None, low: float, high: float) -> float | int | None:
    if value is None:
        return None
    return max(low, min(high, value))


def _enum_or(enum_cls, value: Any, default):
    try:
        return enum_cls(value)
    except ValueError:
        return default


def profile_from_llm(data: dict[str, Any], transcript: str, profession: Profession) -> CandidateProfile:
    speech = candidate_speech(transcript)
    allowed = {s.key for s in skills_for(profession)}

    skills: dict[str, SkillClaim] = {}
    for item in data.get("skills") or []:
        key = item.get("skill")
        if key not in allowed:
            continue
        years = _clamp(item.get("years"), 0, 50)
        evidence = (item.get("evidence") or "").strip()
        if not quote_found(evidence, speech):
            status = "not_found"
        elif not mentions_any(evidence, SKILLS[key].keywords):
            status = "off_topic"
        else:
            status = "found"
        claim = SkillClaim(
            skill=key, years=years, evidence=evidence, verified=status == "found", evidence_status=status
        )
        previous = skills.get(key)
        if previous is None or (claim.verified, claim.years or 0) > (previous.verified, previous.years or 0):
            skills[key] = claim

    certificates: dict[CertKind, CertClaim] = {}
    for item in data.get("certificates") or []:
        kind = _enum_or(CertKind, item.get("kind"), None)
        evidence = (item.get("evidence") or "").strip()
        # Удостоверение без подтверждающей цитаты или с отрицанием («стропального нет») не засчитывается.
        if kind is None or not quote_found(evidence, speech):
            continue
        if NEGATION.search(evidence) and not item.get("level"):
            continue
        certificates[kind] = CertClaim(
            kind=kind,
            level=_clamp(item.get("level"), 1, 8),
            valid=bool(item.get("valid", True)),
            evidence=evidence,
        )

    if CertKind.GRADE not in certificates and (grade := grade_from_speech(speech)):
        certificates[CertKind.GRADE] = grade

    amenities = [_enum_or(Amenity, v, None) for v in data.get("important_amenities") or []]
    salary = data.get("salary_expectation")
    if salary is not None and 0 < salary < 1000:  # «120» вместо «120000»
        salary *= 1000
    zone = data.get("home_zone")

    return CandidateProfile(
        full_name=(data.get("full_name") or "").strip() or "Кандидат",
        profession=profession,
        summary=(data.get("summary") or "").strip(),
        experience_years=_clamp(data.get("experience_years"), 0, 50),
        previous_turnovers=_clamp(data.get("previous_turnovers"), 0, 15),
        skills=list(skills.values()),
        certificates=list(certificates.values()),
        shift_preference=_enum_or(ShiftPreference, data.get("shift_preference"), ShiftPreference.UNKNOWN),
        home_zone=_enum_or(Zone, zone, None) if zone != "unknown" else None,
        has_car=data.get("has_car"),
        stated_commute_minutes=_clamp(data.get("stated_commute_minutes"), 0, 300),
        max_commute_minutes=_clamp(data.get("max_commute_minutes"), 0, 300),
        salary_expectation=_clamp(salary, 10_000, 1_000_000),
        team_preference=_enum_or(TeamPreference, data.get("team_preference"), TeamPreference.UNKNOWN),
        important_amenities=list(dict.fromkeys(a for a in amenities if a)),
    )


async def extract_profile(llm: OllamaClient, transcript: str, vacancy: VacancyData) -> CandidateProfile:
    data = await llm.chat_json(SYSTEM_PROMPT, _user_prompt(transcript, vacancy), extraction_schema(vacancy.profession))
    return profile_from_llm(data, transcript, vacancy.profession)
