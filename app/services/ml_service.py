import logging

from app.core.schemas import CandidateVector

logger = logging.getLogger(__name__)


async def ml_predict(vector: CandidateVector) -> tuple[float, list[str]]:
    """Вызов ML-модуля с 12 признаками."""
    try:
        from app.ml.predictor import RetentionPredictor

        predictor = RetentionPredictor()
        predictor.load_model()

        # Подготовка всех 12 признаков
        features = vector.model_dump()
        # Превращаем enum в int для модели
        features["shift_preference"] = int(features["shift_preference"])

        prediction = predictor.predict_retention(features)
        risk_factors = predictor.explain_prediction(features)
        return float(prediction["retention_probability"]), risk_factors

    except Exception as e:
        logger.error(f"ML Error: {e}")
        return 0.5, ["Ошибка ML-модуля"]
