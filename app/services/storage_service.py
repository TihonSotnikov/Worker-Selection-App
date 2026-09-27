"""
Работа с БД: вакансии, кандидаты, заполнение демо-данными.
"""

import logging
import random

from sqlalchemy import func
from sqlmodel import Session, select

from app.api.models_db import CandidateTable, VacancyTable
from app.core.enums import CandidateSource, Profession
from app.core.schemas import CandidateOut, CandidateProfile, VacancyData, VacancyOut
from app.ml.generator import generate_pool
from app.services.demo_data import DEMO_VACANCIES

logger = logging.getLogger(__name__)


def _vacancy_out(row: VacancyTable, candidates_total: int = 0) -> VacancyOut:
    return VacancyOut(id=row.id, candidates_total=candidates_total, **row.data)


def _candidate_out(row: CandidateTable) -> CandidateOut:
    return CandidateOut(
        id=row.id,
        created_at=row.created_at,
        source=CandidateSource(row.source),
        vacancy_id=row.vacancy_id,
        profile=CandidateProfile.model_validate(row.profile),
        transcript=row.transcript,
    )


def _counts_by_profession(session: Session) -> dict[str, int]:
    rows = session.exec(select(CandidateTable.profession, func.count()).group_by(CandidateTable.profession)).all()
    return dict(rows)


def list_vacancies(session: Session) -> list[VacancyOut]:
    counts = _counts_by_profession(session)
    rows = session.exec(select(VacancyTable).order_by(VacancyTable.id)).all()
    return [_vacancy_out(row, counts.get(row.profession, 0)) for row in rows]


def get_vacancy(session: Session, vacancy_id: int) -> VacancyOut | None:
    row = session.get(VacancyTable, vacancy_id)
    if row is None:
        return None
    return _vacancy_out(row, _counts_by_profession(session).get(row.profession, 0))


def list_candidates(session: Session, profession: Profession | None = None) -> list[CandidateOut]:
    query = select(CandidateTable).order_by(CandidateTable.id)
    if profession is not None:
        query = query.where(CandidateTable.profession == profession.value)
    return [_candidate_out(row) for row in session.exec(query).all()]


def get_candidate(session: Session, candidate_id: int) -> CandidateOut | None:
    row = session.get(CandidateTable, candidate_id)
    return _candidate_out(row) if row else None


def save_candidate(
    session: Session,
    profile: CandidateProfile,
    source: CandidateSource,
    vacancy_id: int | None = None,
    transcript: str | None = None,
    commit: bool = True,
) -> CandidateTable:
    row = CandidateTable(
        source=source.value,
        profession=profile.profession.value,
        full_name=profile.full_name,
        vacancy_id=vacancy_id,
        transcript=transcript,
        profile=profile.model_dump(mode="json"),
    )
    session.add(row)
    if commit:
        session.commit()
        session.refresh(row)
    return row


def save_vacancy(session: Session, data: VacancyData) -> VacancyTable:
    row = VacancyTable(profession=data.profession.value, data=data.model_dump(mode="json"))
    session.add(row)
    return row


def seed_demo_data(session: Session, seed: int) -> None:
    """Заполняет пустую БД демо-вакансиями и синтетическими кандидатами (детерминированно)."""

    if session.exec(select(VacancyTable.id).limit(1)).first() is not None:
        return
    for vacancy in DEMO_VACANCIES:
        save_vacancy(session, vacancy)
    rng = random.Random(seed)
    for profession in Profession:
        for profile in generate_pool(rng, profession):
            save_candidate(session, profile, CandidateSource.SYNTHETIC, commit=False)
    session.commit()
    logger.info("Seeded %d vacancies and synthetic candidates", len(DEMO_VACANCIES))
