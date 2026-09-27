from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# check_same_thread=False нужен SQLite: FastAPI обрабатывает запросы в разных потоках.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=_connect_args)


def init_db() -> None:
    """Создаёт каталог данных и таблицы."""

    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    from app.api import models_db  # noqa: F401  — регистрирует таблицы в metadata

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Сессия БД на время одного HTTP-запроса."""

    with Session(engine) as session:
        yield session
