"""
Расшифровка аудио (STT) через faster-whisper.

Модель загружается один раз при первом обращении и дальше переиспользуется.
Встроенный VAD режет длинные записи на фрагменты речи, поэтому ограничений
на длину файла нет.
"""

import logging
import re
import threading

logger = logging.getLogger(__name__)

# Whisper на паузах иногда «дописывает» фразы из субтитров, на которых учился.
HALLUCINATIONS = re.compile(
    r"(продолжение следует|субтитры (сделал|создавал|подготовил)\w*.*|редактор субтитров.*|"
    r"спасибо за просмотр|подписывайтесь на канал)[.!…]*",
    re.IGNORECASE,
)


def clean_transcript(text: str) -> str:
    return re.sub(r"\s{2,}", " ", HALLUCINATIONS.sub("", text)).strip()


class Transcriber:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self):
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                logger.info("Loading STT model %s...", self.model_name)
                self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            return self._model

    def transcribe(self, path: str) -> str:
        segments, _ = self._get_model().transcribe(
            path, language="ru", vad_filter=True, beam_size=1, condition_on_previous_text=False
        )
        return clean_transcript(" ".join(segment.text.strip() for segment in segments))
