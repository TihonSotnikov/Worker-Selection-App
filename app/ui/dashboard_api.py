from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.ml.feature_contract import FEATURE_COLS
from app.ml.predictor import RetentionPredictor

router = APIRouter(tags=["dashboard"])


def get_status_payload() -> dict[str, Any]:
    return {"status": "ok", "feature_count": len(FEATURE_COLS)}


@router.get("/demo/status")
def demo_status() -> dict[str, Any]:
    try:
        return get_status_payload()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {e}") from e


@router.get("/demo/candidate/{category}")
def get_demo_candidate(category: str) -> dict[str, Any]:
    return {"category": category, "candidate": {}}


@router.post("/demo/predict")
def predict_demo_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    try:
        predictor = RetentionPredictor()
        predictor.load_model()
        return predictor.predict_retention(candidate)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction error: {e}") from e
