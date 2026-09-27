import pytest

from app.ml.predictor import RetentionModel
from app.services.ml_service import BASELINE


@pytest.fixture(scope="module")
def model() -> RetentionModel:
    return RetentionModel.train(3000, 42)


def test_model_quality(model):
    assert model.meta["roc_auc"] > 0.75


def test_night_shift_rule_from_spec(model):
    """ТЗ: кандидаты, не готовые к ночным сменам, в ночь уходят в ~80% случаев."""

    day, night = model.predict([BASELINE, {**BASELINE, "shift_conflict": 2}])
    assert night < 0.35
    assert day - night > 0.4


def test_monotonic_turnovers(model):
    retentions = model.predict([{**BASELINE, "previous_turnovers": n} for n in range(7)])
    assert retentions == sorted(retentions, reverse=True)


def test_explanations_point_to_the_cause(model):
    impacts = model.explain([{**BASELINE, "shift_conflict": 2}])[0]
    assert min(impacts, key=impacts.get) == "shift_conflict"
    assert impacts["shift_conflict"] < -20


def test_save_and_load_roundtrip(model, tmp_path):
    model.save(tmp_path / "m.cbm", tmp_path / "m.json")
    loaded = RetentionModel.load(tmp_path / "m.cbm", tmp_path / "m.json")
    assert loaded is not None
    assert loaded.predict([BASELINE]) == pytest.approx(model.predict([BASELINE]))


def test_explanations_add_up_to_the_prediction(model):
    """Вклады в п.п. складываются в разницу между кандидатом и средним прогнозом."""

    row = {**BASELINE, "previous_turnovers": 5, "commute_minutes": 150, "commute_excess": 90}
    impacts = model.explain([row])[0]
    baseline = model.explain([BASELINE])[0]
    p_row, p_base = model.predict([row, BASELINE])
    assert sum(impacts.values()) - sum(baseline.values()) == pytest.approx((p_row - p_base) * 100, abs=1.0)
    assert impacts["previous_turnovers"] < -10 and impacts["commute_minutes"] + impacts["commute_excess"] < -10
