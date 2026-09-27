from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# check_same_thread=False необходим для SQLite при работе с FastAPI,
# так как каждый запрос обрабатывается в отдельном потоке.
connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,  # Снижение шума логов.
)


def init_db() -> None:
    """
    Синхронное создание таблиц.
    Должно вызываться при старте приложения (main.py @app.on_event("startup")).
    """

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    Генератор-сессия для Dependency Injection в FastAPI.

    Обеспечивает:
        - отдельную транзакцию на каждый HTTP-запрос,
        - автоматическое закрытие сессии после обработки запроса,
        - корректную работу с SQLite в многопоточном режиме.

    Yields
    ------
    Session
        Активная сессия SQLAlchemy/SQLModel, привязанная к текущему запросу.
    """

    with Session(engine) as session:
        yield session
