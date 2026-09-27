import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlmodel import Session

from app.api.database import get_session
from app.core.schemas import CandidateResult
from app.services import interview_service
from app.services.analyze_service import process_candidate
from app.services.storage_service import get_all_candidates

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=CandidateResult, status_code=status.HTTP_201_CREATED)
async def analyze_candidate(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> CandidateResult:
    try:
        model_ext = request.app.state.extractor
        lock = request.app.state.gpu_lock
        return await process_candidate(file, session, model_ext, lock)
    except Exception as e:
        logger.exception("Error processing candidate")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get("/history", response_model=list[CandidateResult])
def get_history(session: Session = Depends(get_session)) -> list[CandidateResult]:
    try:
        return get_all_candidates(session)
    except Exception as e:
        logger.exception("Error fetching history")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch history",
        ) from e


@router.get("/interview/start")
async def start_interview():
    return await interview_service.get_interview_question(0)


@router.post("/interview/submit_answer")
async def submit_answer(step: int, transcript: str):
    return await interview_service.process_interview_answer(step, transcript)


@router.post("/synthesize")
async def synthesize_text(text: str):
    try:
        audio_bytes = interview_service.tts_engine.synthesize(text)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail="TTS error") from e
