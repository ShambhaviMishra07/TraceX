import pytest
from ml_pipeline import score_transaction, FEATURE_COLS, DECISION_THRESHOLD


def make_features(**overrides):
    """Helper: baseline 'normal' feature dict, override specific fields per test."""
    base = {col: 0.0 for col in FEATURE_COLS}
    base.update(overrides)
    return base


def test_score_transaction_returns_expected_keys():
    result = score_transaction(make_features())
    assert set(result.keys()) == {"xgb_proba", "shap_top_feature", "should_investigate"}


def test_score_transaction_proba_is_valid_probability():
    result = score_transaction(make_features())
    assert 0.0 <= result["xgb_proba"] <= 1.0


def test_normal_transaction_has_low_score():
    """All-zero z-scores/changes should look unremarkable to the model."""
    result = score_transaction(make_features())
    assert result["xgb_proba"] < DECISION_THRESHOLD + 0.3  # loose bound, not asserting exact value


def test_extreme_velocity_spike_is_flagged():
    """A large positive z-score on transaction count should push toward investigation."""
    result = score_transaction(make_features(
        txn_count_robust_z=8.0,
        total_amount_robust_z=6.0,
        txn_count_pct_change=3.0,
    ))
    assert result["should_investigate"] is True


def test_shap_top_feature_is_a_known_column():
    result = score_transaction(make_features(refund_rate_robust_z=9.0))
    assert result["shap_top_feature"] in FEATURE_COLS


def test_should_investigate_respects_threshold():
    """Directly checks the gate logic matches the exported threshold, not a hardcoded number."""
    result = score_transaction(make_features())
    expected = result["xgb_proba"] >= DECISION_THRESHOLD
    assert result["should_investigate"] == expected