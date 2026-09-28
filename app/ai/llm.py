"""
Клиент локальной LLM через Ollama (https://ollama.com).

Ответ модели ограничивается JSON-схемой (параметр `format`), поэтому
синтаксически сломанный JSON исключён — остаётся только смысловая проверка.
"""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Ошибка при обращении к LLM."""


class LLMUnavailableError(LLMError):
    """LLM не запущена или модель не скачана."""


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def status(self) -> dict[str, Any]:
        """Проверяет, что Ollama отвечает и нужная модель скачана."""

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
        except httpx.HTTPError:
            return {"available": False, "model": self.model, "detail": "Ollama не запущена"}
        names = {m.get("name") for m in response.json().get("models", [])}
        if self.model not in names:
            return {"available": False, "model": self.model, "detail": f"Модель не скачана: ollama pull {self.model}"}
        return {"available": True, "model": self.model, "detail": "Готова"}

    async def warmup(self) -> None:
        """Загружает модель в память заранее, чтобы первое интервью не ждало."""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.post(
                    f"{self.base_url}/api/generate", json={"model": self.model, "prompt": "", "keep_alive": "30m"}
                )
            logger.info("LLM %s warmed up", self.model)
        except httpx.HTTPError as e:
            logger.warning("LLM warmup skipped: %s", e)

    async def chat_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": schema,
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {"temperature": 0, "num_ctx": 8192},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.ConnectError as e:
            raise LLMUnavailableError("Ollama не запущена. Запустите: brew services start ollama") from e
        except httpx.TimeoutException as e:
            raise LLMError(f"LLM не ответила за {self.timeout:.0f} с") from e
        except httpx.HTTPError as e:
            raise LLMError(f"Соединение с Ollama прервано: {e}") from e

        if response.status_code == 404:
            raise LLMUnavailableError(f"Модель не скачана. Выполните: ollama pull {self.model}")
        if response.status_code >= 400:
            raise LLMError(f"Ollama вернула ошибку {response.status_code}: {response.text[:300]}")

        data = response.json()
        content = data.get("message", {}).get("content", "")
        logger.info(
            "LLM %s: %s prompt tokens, %s output tokens, %.1f s",
            self.model,
            data.get("prompt_eval_count"),
            data.get("eval_count"),
            (data.get("total_duration") or 0) / 1e9,
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMError("LLM вернула некорректный JSON") from e
