"""
Анализ готовой расшифровки или аудиозаписи интервью.
"""

from sqlmodel import Session

from app.ai.extractor import extract_profile
from app.ai.llm import OllamaClient
from app.ai.transcriber import Transcriber
from app.api.models_db import CandidateTable
from app.core.enums import CandidateSource
from app.core.schemas import VacancyOut
from app.services.ai_service import file_to_text
from app.services.storage_service import save_candidate


async def analyze_upload(
    session: Session,
    vacancy: VacancyOut,
    filename: str,
    content: bytes,
    llm: OllamaClient,
    transcriber: Transcriber,
) -> CandidateTable:
    transcript = await file_to_text(filename, content, transcriber)
    profile = await extract_profile(llm, transcript, vacancy)
    return save_candidate(session, profile, CandidateSource.UPLOAD, vacancy.id, transcript)
