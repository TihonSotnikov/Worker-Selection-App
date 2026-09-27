import asyncio
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.ai.extractor import Extractor
from app.ai.transcriber import Transcriber
from app.core.config import settings
from app.core.schemas import CandidateVector


async def save_upload_file(upload_file: UploadFile) -> Path:
    file_extension = Path(upload_file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = Path(settings.UPLOAD_DIR) / unique_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    content = await upload_file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


async def extract_from_file(
    file_path: Path, ext: Extractor, gpu_lock: asyncio.Lock | None = None
) -> tuple[str, str, CandidateVector]:
    extension = file_path.suffix.lower()
    if extension in [".wav", ".mp3"]:
        try:
            stt_model = Transcriber("medium")
            segments, _ = stt_model(str(file_path))
            resume_text = " ".join([segment.text for segment in segments])
        except Exception as e:
            raise HTTPException(status_code=400, detail="Ошибка при обработке аудиофайла") from e
    else:
        with open(file_path, encoding="utf-8") as f:
            resume_text = f.read()

    if gpu_lock:
        async with gpu_lock:
            return await run_in_threadpool(ext, resume_text)
    return await run_in_threadpool(ext, resume_text)
