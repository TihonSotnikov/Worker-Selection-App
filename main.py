import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.ai.llm import OllamaClient
from app.ai.transcriber import Transcriber
from app.api.database import engine, init_db
from app.api.routes import router as api_router
from app.core.config import settings
from app.ml.predictor import RetentionModel
from app.services.storage_service import seed_demo_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent / "app" / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_demo_data(session, settings.SEED)

    app.state.retention_model = RetentionModel.load_or_train(
        settings.model_path, settings.model_meta_path, settings.ML_TRAIN_ROWS, settings.SEED
    )
    app.state.llm = OllamaClient(settings.LLM_BASE_URL, settings.LLM_MODEL, settings.LLM_TIMEOUT)
    app.state.transcriber = Transcriber(settings.STT_MODEL)

    warmup = asyncio.create_task(app.state.llm.warmup()) if settings.LLM_WARMUP else None
    logger.info("Ready: LLM=%s, retention ROC-AUC=%s", settings.LLM_MODEL, app.state.retention_model.meta["roc_auc"])
    yield
    if warmup and not warmup.done():
        warmup.cancel()


app = FastAPI(
    title="Worker Selection App",
    description="Подбор промышленных рабочих: интервью, проверка навыков, шорт-лист с прогнозом удержания",
    version="2.0.0",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
