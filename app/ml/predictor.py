"""
Модель удержания: CatBoost на признаках пары «кандидат × вакансия».

Объяснения строятся на SHAP-значениях CatBoost: для каждого прогноза видно,
на сколько процентных пунктов каждый признак сдвинул вероятность.
"""

import json
import logging
import math
import random
from datetime import UTC, datetime
from pathlib import Path

from catboost import CatBoostClassifier, Pool
from catboost.utils import eval_metric

from app.ml.feature_contract import FEATURE_COLS, MONOTONE
from app.ml.generator import generate_training_data

logger = logging.getLogger(__name__)

MODEL_VERSION = 2


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


class RetentionModel:
    def __init__(self, model: CatBoostClassifier, meta: dict):
        self._model = model
        self.meta = meta

    @classmethod
    def train(cls, rows: int, seed: int) -> "RetentionModel":
        x, y = generate_training_data(rows, seed)
        indices = list(range(rows))
        random.Random(seed).shuffle(indices)
        split = int(rows * 0.8)
        train_idx, test_idx = indices[:split], indices[split:]

        model = CatBoostClassifier(
            iterations=500,
            depth=5,
            learning_rate=0.05,
            l2_leaf_reg=3,
            random_seed=seed,
            monotone_constraints=[MONOTONE[col] for col in FEATURE_COLS],
            verbose=False,
            allow_writing_files=False,
        )
        model.fit(
            Pool([x[i] for i in train_idx], [y[i] for i in train_idx], feature_names=FEATURE_COLS),
        )

        test_pool = Pool([x[i] for i in test_idx], feature_names=FEATURE_COLS)
        probs = model.predict_proba(test_pool)[:, 1]
        roc_auc = eval_metric([y[i] for i in test_idx], probs, "AUC")[0]

        importance = dict(zip(FEATURE_COLS, model.get_feature_importance().tolist(), strict=True))
        meta = {
            "version": MODEL_VERSION,
            "features": FEATURE_COLS,
            "rows": rows,
            "seed": seed,
            "roc_auc": round(float(roc_auc), 3),
            "baseline_retention": round(sum(y) / len(y), 3),
            "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "importance": {k: round(v, 1) for k, v in sorted(importance.items(), key=lambda kv: -kv[1])},
        }
        logger.info("Retention model trained: ROC-AUC=%.3f on %d rows", roc_auc, rows)
        return cls(model, meta)

    def save(self, model_path: Path, meta_path: Path) -> None:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        self._model.save_model(str(model_path))
        meta_path.write_text(json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, model_path: Path, meta_path: Path) -> "RetentionModel | None":
        if not model_path.exists() or not meta_path.exists():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("version") != MODEL_VERSION or meta.get("features") != FEATURE_COLS:
            logger.info("Saved retention model is outdated, retraining")
            return None
        model = CatBoostClassifier()
        model.load_model(str(model_path))
        return cls(model, meta)

    @classmethod
    def load_or_train(cls, model_path: Path, meta_path: Path, rows: int, seed: int) -> "RetentionModel":
        model = cls.load(model_path, meta_path)
        if model is None:
            model = cls.train(rows, seed)
            model.save(model_path, meta_path)
        return model

    def _pool(self, rows: list[dict[str, float]]) -> Pool:
        return Pool([[float(r[col]) for col in FEATURE_COLS] for r in rows], feature_names=FEATURE_COLS)

    def predict(self, rows: list[dict[str, float]]) -> list[float]:
        if not rows:
            return []
        return [float(p) for p in self._model.predict_proba(self._pool(rows))[:, 1]]

    def explain(self, rows: list[dict[str, float]]) -> list[dict[str, float]]:
        """
        Вклад каждого признака в прогноз, в процентных пунктах вероятности удержания.

        SHAP-значения CatBoost аддитивны в логитах. Чтобы вклады в процентах тоже
        складывались, они масштабируются секущей сигмоиды между средним прогнозом
        (base) и прогнозом кандидата: сумма вкладов = p(кандидат) − p(средний).
        Знак каждого вклада сохраняется, потому что сигмоида монотонна.
        """

        if not rows:
            return []
        shap = self._model.get_feature_importance(data=self._pool(rows), type="ShapValues")
        result = []
        for row in shap:
            base = float(row[-1])
            delta_logit = float(row[:-1].sum())
            p_base, p_full = _sigmoid(base), _sigmoid(base + delta_logit)
            slope = (p_full - p_base) / delta_logit if abs(delta_logit) > 1e-6 else p_base * (1 - p_base)
            result.append({col: round(float(row[i]) * slope * 100, 1) for i, col in enumerate(FEATURE_COLS)})
        return result
