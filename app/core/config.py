from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Конфигурация приложения. Значения берутся из переменных окружения или файла .env.

    Attributes
    ----------
    DATA_DIR : Path
        Каталог для базы, обученной модели и временных загрузок.
    DATABASE_URL : str
        Строка подключения к БД. По умолчанию SQLite в DATA_DIR.
    LLM_BASE_URL : str
        Адрес Ollama.
    LLM_MODEL : str
        Имя модели в Ollama.
    LLM_TIMEOUT : float
        Таймаут одного запроса к LLM, секунд.
    LLM_WARMUP : bool
        Загружать ли модель в память при старте приложения.
    STT_MODEL : str
        Модель faster-whisper для расшифровки аудио.
    ML_TRAIN_ROWS : int
        Размер синтетической выборки для обучения модели удержания.
    SEED : int
        Зерно генераторов — демо-данные и модель воспроизводимы.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATA_DIR: Path = PROJECT_ROOT / "data"
    DATABASE_URL: str = ""

    LLM_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_MODEL: str = "qwen3.5:9b"
    LLM_TIMEOUT: float = 300.0
    LLM_WARMUP: bool = True

    STT_MODEL: str = "large-v3-turbo"

    ML_TRAIN_ROWS: int = 6000
    SEED: int = 42

    MAX_UPLOAD_MB: int = 25

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL or f"sqlite:///{self.DATA_DIR / 'app.db'}"

    @property
    def model_path(self) -> Path:
        return self.DATA_DIR / "retention_model.cbm"

    @property
    def model_meta_path(self) -> Path:
        return self.DATA_DIR / "retention_model.json"


settings = Settings()
