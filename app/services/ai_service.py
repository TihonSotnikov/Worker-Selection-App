"""
Превращение загруженного файла в текст расшифровки.
"""

import tempfile
from pathlib import Path

import av
from fastapi.concurrency import run_in_threadpool

from app.ai.transcriber import Transcriber

TEXT_EXTENSIONS = {".txt", ".md"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac", ".aiff"}


class UnsupportedFileError(ValueError):
    """Файл нельзя превратить в текст."""


def decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnsupportedFileError("Не удалось прочитать текст: ожидается UTF-8 или Windows-1251")


async def file_to_text(filename: str, content: bytes, transcriber: Transcriber) -> str:
    extension = Path(filename or "").suffix.lower()
    if extension in TEXT_EXTENSIONS:
        text = decode_text(content)
    elif extension in AUDIO_EXTENSIONS:
        with tempfile.NamedTemporaryFile(suffix=extension) as tmp:
            tmp.write(content)
            tmp.flush()
            try:
                text = await run_in_threadpool(transcriber.transcribe, tmp.name)
            except av.error.FFmpegError as e:
                raise UnsupportedFileError("Не удалось прочитать аудио: файл повреждён или это не аудиозапись") from e
    else:
        supported = ", ".join(sorted(TEXT_EXTENSIONS | AUDIO_EXTENSIONS))
        raise UnsupportedFileError(f"Формат {extension or 'без расширения'} не поддерживается. Можно: {supported}")

    if len(text.strip()) < 30:
        raise UnsupportedFileError("В файле почти нет текста — нечего анализировать")
    return text
