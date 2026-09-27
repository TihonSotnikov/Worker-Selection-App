"""
«Что выучила модель»: прогноз для типичного кандидата и как его меняет один фактор.
"""

from app.ml.predictor import RetentionModel

BASELINE: dict[str, float] = {
    "experience_years": 5,
    "previous_turnovers": 1,
    "skill_coverage": 1.0,
    "shift_conflict": 0,
    "commute_minutes": 30,
    "commute_excess": 0,
    "salary_gap_pct": 0.0,
    "amenities_missing": 0,
    "team_mismatch": 0,
}

SCENARIOS: list[tuple[str, dict[str, float]]] = [
    ("Не готов к ночным сменам, а вакансия ночная", {"shift_conflict": 2}),
    ("Хочет только день, а график 2/2 с ночами", {"shift_conflict": 1}),
    ("4–5 смен работы за последние 5 лет", {"previous_turnovers": 5}),
    ("Зарплата на 25% ниже ожиданий", {"salary_gap_pct": -0.25}),
    ("Дорога 100 минут при допустимых 60", {"commute_minutes": 100, "commute_excess": 40}),
    ("Навыки закрывают требования наполовину", {"skill_coverage": 0.5}),
]


def model_insights(model: RetentionModel) -> dict:
    rows = [BASELINE] + [{**BASELINE, **change} for _, change in SCENARIOS]
    predictions = model.predict(rows)
    baseline = predictions[0]
    return {
        "baseline": round(baseline, 3),
        "scenarios": [
            {"label": label, "retention": round(p, 3), "delta": round((p - baseline) * 100, 1)}
            for (label, _), p in zip(SCENARIOS, predictions[1:], strict=True)
        ],
    }
