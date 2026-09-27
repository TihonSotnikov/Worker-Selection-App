import logging

from app.ai.interviewer import Interviewer
from app.ai.tts import TextToSpeechEngine

logger = logging.getLogger(__name__)

# Синглтоны для простоты MVP
tts_engine = TextToSpeechEngine()
interviewer = Interviewer()


async def get_interview_question(step: int) -> dict:
    """
    Подготавливает вопрос для фронтенда: текст + аудио.
    """
    text = interviewer.get_question(step)
    if not text:
        return {"finished": True}

    # В реальном сценарии здесь будет кэширование аудио
    # audio_content = tts_engine.synthesize(text)

    return {"step": step, "text": text, "finished": False}


async def process_interview_answer(step: int, transcript: str) -> dict:
    """
    Логика обработки ответа.
    """
    logger.info(f"Step {step} transcript: {transcript}")

    next_step = step + 1
    next_q = await get_interview_question(next_step)

    return {"received": True, "next_question": next_q}
