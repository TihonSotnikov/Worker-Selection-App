import random

from app.core.enums import (
    CandidateSource,
    CheckStatus,
    Profession,
    ShiftPreference,
    ShiftSchedule,
    TeamFormat,
    TeamPreference,
    Zone,
)
from app.core.schemas import CandidateOut, CandidateProfile, SkillClaim, SkillRequirement, VacancyOut
from app.ml.feature_contract import assess_skill, build_features, shift_conflict, team_mismatch
from app.ml.generator import generate_pool
from app.ml.predictor import RetentionModel
from app.services.demo_data import DEMO_VACANCIES
from app.services.matching_service import build_reports, shortlist


def _vacancy(index: int = 2) -> VacancyOut:
    return VacancyOut(id=index + 1, **DEMO_VACANCIES[index].model_dump())


def _candidate(candidate_id: int, profile: CandidateProfile, vacancy_id: int | None = None) -> CandidateOut:
    return CandidateOut(
        id=candidate_id,
        created_at="2026-01-01T00:00:00Z",
        source=CandidateSource.SYNTHETIC,
        vacancy_id=vacancy_id,
        profile=profile,
    )


def test_shift_conflict_matrix():
    assert shift_conflict(ShiftPreference.DAY_ONLY, ShiftSchedule.NIGHT) == 2
    assert shift_conflict(ShiftPreference.DAY_ONLY, ShiftSchedule.ROTATING) == 1
    assert shift_conflict(ShiftPreference.DAY_ONLY, ShiftSchedule.DAY) == 0
    assert shift_conflict(ShiftPreference.ANY, ShiftSchedule.NIGHT) == 0
    assert shift_conflict(ShiftPreference.UNKNOWN, ShiftSchedule.NIGHT) == 0


def test_team_mismatch():
    assert team_mismatch(TeamPreference.SOLO, TeamFormat.TEAM)
    assert not team_mismatch(TeamPreference.ANY, TeamFormat.TEAM)


def test_assess_skill_statuses():
    req = SkillRequirement(skill="tig", min_years=3)
    assert assess_skill(None, req).status == CheckStatus.MISSING
    assert assess_skill(SkillClaim(skill="tig", years=5, verified=True), req).status == CheckStatus.OK

    unverified = assess_skill(SkillClaim(skill="tig", years=5, verified=False), req)
    assert unverified.status == CheckStatus.PARTIAL and unverified.score == 0.7

    short = assess_skill(SkillClaim(skill="tig", years=1.5, verified=True), req)
    assert short.status == CheckStatus.PARTIAL and 0.2 <= short.score < 0.7
    assert "от 3 лет" in short.note


def test_stated_commute_used_only_for_interview_vacancy():
    vacancy = DEMO_VACANCIES[2]
    profile = CandidateProfile(
        full_name="Тест", profession=Profession.WELDER, home_zone=Zone.NORTH, stated_commute_minutes=20
    )
    _, stated = build_features(profile, vacancy, stated_applies=True)
    _, zones = build_features(profile, vacancy, stated_applies=False)
    assert stated.commute_minutes == 20 and stated.commute_source == "stated"
    assert zones.commute_minutes == 75 and zones.commute_source == "zones"


def test_unknown_facts_become_clarifications():
    model = RetentionModel.train(1500, 7)
    vacancy = _vacancy()
    profile = CandidateProfile(
        full_name="Неизвестный",
        profession=Profession.WELDER,
        skills=[SkillClaim(skill="tig", years=None, evidence="", verified=False)],
    )
    report = build_reports(model, vacancy, [_candidate(1, profile)])[0]
    assert not report.passes_requirements  # второй обязательный навык не назван
    assert any("ночным" in item for item in report.clarify)
    assert any("Зарплатные" in item for item in report.clarify)


def test_shortlist_contains_only_candidates_with_required_skills():
    model = RetentionModel.train(1500, 7)
    vacancy = _vacancy()
    pool = generate_pool(random.Random(1), Profession.WELDER)
    candidates = [_candidate(i + 1, p) for i, p in enumerate(pool)]

    result = shortlist(model, vacancy, candidates)

    assert 0 < len(result.shortlist) <= 5
    assert all(r.passes_requirements for r in result.shortlist)
    scores = [r.final_score for r in result.shortlist]
    assert scores == sorted(scores, reverse=True)
    assert [r.rank for r in result.shortlist] == list(range(1, len(result.shortlist) + 1))
    assert len(result.shortlist) + len(result.others) == len(candidates)


def test_llm_claims_without_evidence_do_not_count():
    req = SkillRequirement(skill="blueprints", min_years=2)
    off_topic = SkillClaim(skill="blueprints", years=5, evidence="допуски до сотки держал", evidence_status="off_topic")
    not_found = SkillClaim(skill="blueprints", years=5, evidence="читаю чертежи", evidence_status="not_found")
    assert assess_skill(off_topic, req).status == CheckStatus.MISSING
    assert assess_skill(not_found, req).status == CheckStatus.MISSING
