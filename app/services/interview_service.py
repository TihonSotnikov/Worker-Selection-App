"""
Сессии интервью: выдача вопросов, приём ответов, финальный разбор через LLM.
"""

from sqlmodel import Session

from app.ai.extractor import extract_profile
from app.ai.interviewer import CLOSING, build_script, format_transcript
from app.ai.llm import OllamaClient
from app.api.models_db import InterviewTable
from app.core.enums import CandidateSource
from app.core.schemas import InterviewMessage, InterviewOut, VacancyOut
from app.services.storage_service import save_candidate


class InterviewStateError(ValueError):
    """Действие недопустимо в текущем состоянии интервью."""


def to_out(row: InterviewTable) -> InterviewOut:
    return InterviewOut(
        id=row.id,
        vacancy_id=row.vacancy_id,
        status=row.status,
        step=row.step,
        total_questions=len(row.questions),
        messages=[InterviewMessage(**m) for m in row.messages],
        candidate_id=row.candidate_id,
        error=row.error,
    )


def start(session: Session, vacancy: VacancyOut) -> InterviewTable:
    questions = build_script(vacancy)
    first = questions[0]
    row = InterviewTable(
        vacancy_id=vacancy.id,
        questions=questions,
        messages=[{"role": "assistant", "text": first["text"], "key": first["key"]}],
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def answer(session: Session, row: InterviewTable, text: str) -> InterviewTable:
    if row.status != "active":
        raise InterviewStateError("Интервью уже завершено")
    question = row.questions[row.step]
    messages = [*row.messages, {"role": "candidate", "text": text.strip(), "key": question["key"]}]
    row.step += 1
    if row.step < len(row.questions):
        following = row.questions[row.step]
        messages.append({"role": "assistant", "text": following["text"], "key": following["key"]})
    else:
        messages.append({"role": "assistant", "text": CLOSING, "key": "closing"})
        row.status = "ready"
    row.messages = messages  # новый список — SQLAlchemy увидит изменение JSON
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


async def finish(session: Session, row: InterviewTable, vacancy: VacancyOut, llm: OllamaClient) -> InterviewTable:
    """Разбирает ответы через LLM и создаёт кандидата. Можно завершить и досрочно."""

    if row.status == "done":
        return row
    if not any(m["role"] == "candidate" for m in row.messages):
        raise InterviewStateError("Кандидат ещё не ответил ни на один вопрос")

    transcript = format_transcript([InterviewMessage(**m) for m in row.messages if m.get("key") != "closing"])
    try:
        profile = await extract_profile(llm, transcript, vacancy)
    except Exception as e:
        row.error = str(e)
        session.add(row)
        session.commit()
        raise

    candidate = save_candidate(session, profile, CandidateSource.INTERVIEW, vacancy.id, transcript, commit=False)
    session.flush()
    row.candidate_id = candidate.id
    row.status = "done"
    row.error = None
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
