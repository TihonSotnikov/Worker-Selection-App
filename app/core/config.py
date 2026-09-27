from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Глобальная конфигурация приложения на основе переменных окружения.

    Загружает настройки из переменных ОС или файла .env.
    Обеспечивает проверку типов и значения по умолчанию для критически важных параметров.

    Attributes
    ----------
    OPENAI_API_KEY : str
        API-ключ для аутентификации в сервисах OpenAI.
        По умолчанию: "not-set" (использование только для разработки/тестов).
    DATABASE_URL : str
        Строка подключения к SQL-базе данных.
        По умолчанию: "sqlite:///./Worker_Selection_App.db" (локальный файл SQLite).
    UPLOAD_DIR : str
        Путь в файловой системе для временного хранения загруженных резюме.
        По умолчанию: "/tmp/Worker_Selection_App_uploads".
    """

    OPENAI_API_KEY: str = "not-set"
    DATABASE_URL: str = "sqlite:///./Worker_Selection_App.db"
    UPLOAD_DIR: str = "/tmp/Worker_Selection_App_uploads"

    model_config = ConfigDict(env_file=".env")


# Создаётся единственный экземпляр, который импортируется по всему приложению.
# Это немедленно запускает валидацию переменных окружения при импорте.
settings = Settings()
