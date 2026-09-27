import json

from sqlmodel import Session, select

from app.api.models_db import CandidateTable
from app.core.enums import ShiftPreference
from app.core.schemas import CandidateResult, CandidateVector


def save_candidate(
    session: Session,
    full_name: str,
    raw_summary: str,
    retention_score: float,
    risk_factors: list[str],
    vector: CandidateVector,
) -> CandidateTable:
    """Сохраняет 12 признаков кандидата."""
    db_candidate = CandidateTable(
        full_name=full_name,
        raw_summary=raw_summary,
        retention_score=retention_score,
        risk_factors=json.dumps(risk_factors, ensure_ascii=False),
        vec_skills_count=vector.skills_verified_count,
        vec_years_experience=vector.years_experience,
        vec_age=vector.age,
        vec_commute_minutes=vector.commute_time_minutes,
        vec_shift_preference=int(vector.shift_preference),
        vec_salary_expectation=vector.salary_expectation,
        vec_has_certifications=vector.has_certifications,
        vec_education_level=vector.education_level,
        vec_previous_turnovers=vector.previous_turnovers,
        vec_family_status=vector.family_status,
        vec_housing_type=vector.housing_type,
        vec_has_transport=vector.has_transport,
    )
    session.add(db_candidate)
    session.commit()
    session.refresh(db_candidate)
    return db_candidate


def get_all_candidates(session: Session) -> list[CandidateResult]:
    """Загружает кандидатов с 12 признаками."""
    candidates = session.exec(select(CandidateTable).order_by(CandidateTable.created_at.desc())).all()
    results = []
    for db in candidates:
        vector = CandidateVector(
            skills_verified_count=db.vec_skills_count,
            years_experience=db.vec_years_experience,
            age=db.vec_age,
            commute_time_minutes=db.vec_commute_minutes,
            shift_preference=ShiftPreference(db.vec_shift_preference),
            salary_expectation=db.vec_salary_expectation,
            has_certifications=db.vec_has_certifications,
            education_level=db.vec_education_level,
            previous_turnovers=db.vec_previous_turnovers,
            family_status=db.vec_family_status,
            housing_type=db.vec_housing_type,
            has_transport=db.vec_has_transport,
        )
        results.append(
            CandidateResult(
                id=str(db.id),
                full_name=db.full_name,
                raw_summary=db.raw_summary,
                vector=vector,
                retention_score=db.retention_score,
                risk_factors=json.loads(db.risk_factors),
            )
        )
    return results
