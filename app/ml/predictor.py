import os
import pickle
from typing import Any

import catboost as cb
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from app.ml.feature_contract import FEATURE_COLS, FEATURE_DEFAULTS

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_PATH = os.path.join(CURRENT_DIR, "model.pkl")
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
DEFAULT_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "train_dataset.csv")


class RetentionPredictor:
    """
    ML Модель для предсказания удержания кандидата.
    """

    def __init__(self):
        self.model = None
        self.feature_names = None
        self._prediction_cache = {}
        self._explain_cache = {}
        self._positive_cache = {}

    def _map_risk_level(self, retention_probability: float) -> str:
        if retention_probability >= 0.7:
            return "LOW"
        if retention_probability >= 0.4:
            return "MEDIUM"
        return "HIGH"

    def _detect_requires_review(self, features: dict) -> bool:
        return features.get("years_experience", 0) <= 0

    def _estimate_uncertainty_band(
        self,
        retention_probability: float,
        features: dict,
        requires_review: bool = False,
    ) -> dict:
        if requires_review:
            margin = 0.12
        elif 0.4 <= retention_probability < 0.7:
            margin = 0.08
        elif retention_probability < 0.4:
            margin = 0.06
        else:
            margin = 0.05

        return {
            "uncertainty_low": max(0.0, retention_probability - margin),
            "uncertainty_high": min(1.0, retention_probability + margin),
            "uncertainty_margin": margin,
            "uncertainty_note": "Ориентировочный коридор неопределённости.",
        }

    def _prepare_feature_df(self, features: dict) -> pd.DataFrame:
        features = {**FEATURE_DEFAULTS, **dict(features)}
        return pd.DataFrame([features])[self.feature_names]

    def _rule_based_weighted_risks(self, features: dict) -> list[str]:
        features = {**FEATURE_DEFAULTS, **dict(features)}
        scored_risks = []

        def add(condition: bool, weight: float, text: str):
            if condition:
                scored_risks.append((weight, text))

        add(features.get("years_experience", 0) <= 0, 3.5, "Требуется уточнение опыта")
        add(features.get("commute_time_minutes", 0) > 120, 3.0, "Очень длинная дорога до работы")
        add(features.get("previous_turnovers", 0) > 3, 3.2, "Частая смена прошлых мест работы")

        scored_risks.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored_risks][:3]

    def train_model(self, data_path: str = DEFAULT_DATA_PATH) -> Any:
        df = pd.read_csv(data_path)
        feature_cols = FEATURE_COLS
        x = df[feature_cols]
        y = df["retention"]
        self.feature_names = feature_cols

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)

        self.model = cb.CatBoostClassifier(
            iterations=500,
            depth=6,
            learning_rate=0.1,
            loss_function="Logloss",
            verbose=False,
            random_state=42,
            allow_writing_files=False,
        )
        self.model.fit(x_train, y_train, eval_set=(x_test, y_test))

        y_pred_proba = self.model.predict_proba(x_test)[:, 1]
        print(f"ROC-AUC: {roc_auc_score(y_test, y_pred_proba):.3f}")
        return self.model

    def predict_retention(self, features: dict) -> dict:
        if self.model is None:
            raise ValueError("Model is not loaded.")
        feature_df = self._prepare_feature_df(features)
        retention_prob = float(self.model.predict_proba(feature_df)[0, 1])
        requires_review = self._detect_requires_review(features)
        risk_level = "MEDIUM" if requires_review else self._map_risk_level(retention_prob)

        uncertainty = self._estimate_uncertainty_band(retention_prob, features, requires_review)
        return {
            "retention_probability": retention_prob,
            "will_stay": bool(retention_prob > 0.5),
            "risk_level": risk_level,
            "requires_review": requires_review,
            **uncertainty,
        }

    def explain_prediction(self, features: dict) -> list[str]:
        return self._rule_based_weighted_risks(features)

    def explain_positive_factors(self, features: dict) -> list[str]:
        positives = []
        if features.get("skills_verified_count", 0) >= 7:
            positives.append("Много подтверждённых навыков")
        return positives[:3]

    def save_model(self, path: str = DEFAULT_MODEL_PATH) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "feature_names": self.feature_names}, f)

    def load_model(self, path: str = DEFAULT_MODEL_PATH) -> bool:
        if not os.path.exists(path):
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.feature_names = data["feature_names"]
        return True


def train_if_needed() -> None:
    model = RetentionPredictor()
    if not model.load_model(DEFAULT_MODEL_PATH):
        model.train_model(DEFAULT_DATA_PATH)
        model.save_model(DEFAULT_MODEL_PATH)
