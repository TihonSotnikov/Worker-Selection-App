from pathlib import Path

from app.ai.extractor import candidate_speech, extraction_schema, profile_from_llm, quote_found
from app.core.enums import Amenity, CertKind, Profession, ShiftPreference
from tests.conftest import WELDER_EXTRACTION

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

TRANSCRIPT = """Рекрутер: Как вас зовут?

Кандидат: Пётр. Аргоном варю пять лет, в основном нержавейка.

Рекрутер: Удостоверения?

Кандидат: НАКС есть, продлевал весной."""


def test_candidate_speech_keeps_only_candidate_lines():
    speech = candidate_speech(TRANSCRIPT)
    assert "Аргоном варю" in speech
    assert "Как вас зовут" not in speech


def test_candidate_speech_on_example_file():
    text = (EXAMPLES / "candidate1.txt").read_text(encoding="utf-8")
    speech = candidate_speech(text)
    assert "Fanuc" in speech
    assert "виртуальный ассистент" not in speech


def test_quote_found_tolerates_small_differences():
    speech = candidate_speech(TRANSCRIPT)
    assert quote_found("Аргоном варю пять лет, в основном нержавейка", speech)
    assert quote_found("аргоном варю 5 лет, в основном нержавейка", speech)  # одно слово записано цифрой
    assert quote_found("аргоном варю пять лет в основном нержавейку", speech)  # другое окончание
    assert not quote_found("Полуавтоматом варю десять лет, металлоконструкции", speech)
    assert not quote_found("Работал на Fanuc десять лет", speech)
    assert not quote_found("нержавейка", speech)  # слишком короткая цитата ничего не доказывает


def test_profile_from_llm_validates_and_verifies():
    profile = profile_from_llm(WELDER_EXTRACTION, TRANSCRIPT, Profession.WELDER)
    skills = {s.skill: s for s in profile.skills}

    assert set(skills) == {"tig", "stainless"}  # навык чужой профессии отброшен
    assert skills["tig"].verified
    assert not skills["stainless"].verified  # выдуманная цитата не подтверждает навык
    assert profile.salary_expectation == 120_000  # «120» → тысячи рублей
    assert profile.shift_preference == ShiftPreference.DAY_ONLY
    assert profile.important_amenities == [Amenity.CANTEEN]


def test_profile_from_llm_handles_garbage():
    profile = profile_from_llm(
        {"full_name": "", "shift_preference": "sometimes", "home_zone": "unknown", "skills": None},
        TRANSCRIPT,
        Profession.WELDER,
    )
    assert profile.full_name == "Кандидат"
    assert profile.shift_preference == ShiftPreference.UNKNOWN
    assert profile.home_zone is None
    assert profile.skills == []


def test_schema_limits_skills_to_profession():
    schema = extraction_schema(Profession.CNC)
    skill_enum = schema["properties"]["skills"]["items"]["properties"]["skill"]["enum"]
    assert "fanuc" in skill_enum and "tig" not in skill_enum


def test_grade_mentioned_in_passing_is_not_lost():
    transcript = (EXAMPLES / "candidate1.txt").read_text(encoding="utf-8")
    profile = profile_from_llm({"full_name": "Дмитрий", "certificates": []}, transcript, Profession.CNC)
    grade = next(c for c in profile.certificates if c.kind == CertKind.GRADE)
    assert grade.level == 5 and grade.valid
    assert "5-й разряд" in grade.evidence


def test_absent_certificate_is_dropped():
    transcript = "Кандидат: Стропального нет, но готов отучиться."
    data = {"certificates": [{"kind": "slinger", "level": None, "valid": False, "evidence": "Стропального нет"}]}
    assert profile_from_llm(data, transcript, Profession.CNC).certificates == []


def test_off_topic_quote_does_not_verify_skill():
    transcript = "Кандидат: Я и слесарь, и электрик, и киповец, всё умею делать сам."
    data = {"skills": [{"skill": "hydraulics", "years": 5, "evidence": "и слесарь, и электрик, и киповец"}]}
    claim = profile_from_llm(data, transcript, Profession.ELECTRO).skills[0]
    assert claim.evidence_status == "off_topic"
    assert not claim.verified
