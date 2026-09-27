import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlmodel import Session

from app.ai.llm import LLMError, LLMUnavailableError, OllamaClient
from app.ai.transcriber import Transcriber
from app.api.database import get_session
from app.api.models_db import InterviewTable
from app.core.catalog import (
    AMENITY_LABELS,
    CERT_LABELS,
    PROFESSION_LABELS,
    SHIFT_SCHEDULE_LABELS,
    SKILLS,
    TEAM_FORMAT_LABELS,
    ZONE_LABELS,
)
from app.core.config import settings
from app.core.schemas import (
    AnswerIn,
    CandidateReportOut,
    InterviewCreateIn,
    InterviewOut,
    ShortlistOut,
    VacancyOut,
)
from app.ml.predictor import RetentionModel
from app.services import interview_service, storage_service
from app.services.ai_service import UnsupportedFileError
from app.services.analyze_service import analyze_upload
from app.services.matching_service import build_reports, shortlist
from app.services.ml_service import model_insights

logger = logging.getLogger(__name__)
router = APIRouter()


def get_llm(request: Request) -> OllamaClient:
    return request.app.state.llm


def get_model(request: Request) -> RetentionModel:
    return request.app.state.retention_model


def get_transcriber(request: Request) -> Transcriber:
    return request.app.state.transcriber


def _vacancy_or_404(session: Session, vacancy_id: int) -> VacancyOut:
    vacancy = storage_service.get_vacancy(session, vacancy_id)
    if vacancy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вакансия не найдена")
    return vacancy


def _interview_or_404(session: Session, interview_id: int) -> InterviewTable:
    row = session.get(InterviewTable, interview_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Интервью не найдено")
    return row


def _llm_http_error(e: LLMError) -> HTTPException:
    code = status.HTTP_503_SERVICE_UNAVAILABLE if isinstance(e, LLMUnavailableError) else status.HTTP_502_BAD_GATEWAY
    return HTTPException(code, str(e))


# ---------------------------------------------------------------------------
# Система
# ---------------------------------------------------------------------------


@router.get("/status")
async def get_status(llm: OllamaClient = Depends(get_llm), model: RetentionModel = Depends(get_model)) -> dict:
    return {
        "llm": await llm.status(),
        "stt": {"model": settings.STT_MODEL},
        "ml": {
            "roc_auc": model.meta["roc_auc"],
            "rows": model.meta["rows"],
            "trained_at": model.meta["trained_at"],
            "importance": model.meta["importance"],
        },
        "insights": model_insights(model),
    }


@router.get("/catalog")
def get_catalog() -> dict:
    """Подписи справочников для интерфейса."""

    return {
        "professions": PROFESSION_LABELS,
        "skills": {key: skill.label for key, skill in SKILLS.items()},
        "certificates": CERT_LABELS,
        "shifts": SHIFT_SCHEDULE_LABELS,
        "zones": ZONE_LABELS,
        "amenities": AMENITY_LABELS,
        "team_formats": TEAM_FORMAT_LABELS,
    }


# ---------------------------------------------------------------------------
# Вакансии и шорт-листы
# ---------------------------------------------------------------------------


@router.get("/vacancies", response_model=list[VacancyOut])
def list_vacancies(session: Session = Depends(get_session)) -> list[VacancyOut]:
    return storage_service.list_vacancies(session)


@router.get("/vacancies/{vacancy_id}", response_model=VacancyOut)
def get_vacancy(vacancy_id: int, session: Session = Depends(get_session)) -> VacancyOut:
    return _vacancy_or_404(session, vacancy_id)


@router.get("/vacancies/{vacancy_id}/shortlist", response_model=ShortlistOut)
def get_shortlist(
    vacancy_id: int,
    session: Session = Depends(get_session),
    model: RetentionModel = Depends(get_model),
) -> ShortlistOut:
    vacancy = _vacancy_or_404(session, vacancy_id)
    return shortlist(model, vacancy, storage_service.list_candidates(session, vacancy.profession))


@router.get("/vacancies/{vacancy_id}/candidates/{candidate_id}", response_model=CandidateReportOut)
def get_candidate_report(
    vacancy_id: int,
    candidate_id: int,
    session: Session = Depends(get_session),
    model: RetentionModel = Depends(get_model),
) -> CandidateReportOut:
    vacancy = _vacancy_or_404(session, vacancy_id)
    candidate = storage_service.get_candidate(session, candidate_id)
    if candidate is None or candidate.profile.profession != vacancy.profession:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Кандидат не найден среди кандидатов этой вакансии")
    reports = build_reports(model, vacancy, storage_service.list_candidates(session, vacancy.profession))
    report = next(r for r in reports if r.candidate_id == candidate_id)
    return CandidateReportOut(
        vacancy=vacancy,
        candidate=candidate,
        report=report,
        shortlist_size=sum(1 for r in reports if r.passes_requirements),
    )


@router.post("/vacancies/{vacancy_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_interview(
    vacancy_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    llm: OllamaClient = Depends(get_llm),
    transcriber: Transcriber = Depends(get_transcriber),
) -> dict:
    vacancy = _vacancy_or_404(session, vacancy_id)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Файл больше {settings.MAX_UPLOAD_MB} МБ")
    try:
        candidate = await analyze_upload(session, vacancy, file.filename or "", content, llm, transcriber)
    except UnsupportedFileError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except LLMError as e:
        raise _llm_http_error(e) from e
    return {"candidate_id": candidate.id}


# ---------------------------------------------------------------------------
# Интервью
# ---------------------------------------------------------------------------


@router.post("/interviews", response_model=InterviewOut, status_code=status.HTTP_201_CREATED)
def create_interview(body: InterviewCreateIn, session: Session = Depends(get_session)) -> InterviewOut:
    vacancy = _vacancy_or_404(session, body.vacancy_id)
    return interview_service.to_out(interview_service.start(session, vacancy))


@router.get("/interviews/{interview_id}", response_model=InterviewOut)
def get_interview(interview_id: int, session: Session = Depends(get_session)) -> InterviewOut:
    return interview_service.to_out(_interview_or_404(session, interview_id))


@router.post("/interviews/{interview_id}/answer", response_model=InterviewOut)
def answer_interview(interview_id: int, body: AnswerIn, session: Session = Depends(get_session)) -> InterviewOut:
    row = _interview_or_404(session, interview_id)
    try:
        return interview_service.to_out(interview_service.answer(session, row, body.text))
    except interview_service.InterviewStateError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e


@router.post("/interviews/{interview_id}/finish", response_model=InterviewOut)
async def finish_interview(
    interview_id: int,
    session: Session = Depends(get_session),
    llm: OllamaClient = Depends(get_llm),
) -> InterviewOut:
    row = _interview_or_404(session, interview_id)
    vacancy = _vacancy_or_404(session, row.vacancy_id)
    try:
        row = await interview_service.finish(session, row, vacancy, llm)
    except interview_service.InterviewStateError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    except LLMError as e:
        raise _llm_http_error(e) from e
    return interview_service.to_out(row)
