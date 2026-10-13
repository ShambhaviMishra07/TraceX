import os
import numpy as np
import xgboost as xgb
import joblib
import shap

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _p(name):
    return os.path.join(BASE_DIR, name)


_REFUND_BASE = ["refund_rate", "refund_value_ratio", "repeat_refund_customer_share",
                "avg_refund_latency_days", "post_settlement_refund_share"]

# One entry per loss class. Adding a third class = one more entry + trained artifacts.
LOSS_CLASSES = {
    "txn_spike": {
        "label": "Transaction spike",
        "model_path": _p("xgb_fraud_spike.json"),
        "threshold_path": _p("decision_threshold.pkl"),
        "cost_curve_path": _p("cost_curve.json"),
        "feature_cols": [
            "txn_count_robust_z", "total_amount_robust_z",
            "refund_rate_robust_z", "unique_devices_robust_z",
            "txn_count_pct_change", "total_amount_pct_change",
            "refund_rate_pct_change", "unique_devices_pct_change",
            "failed_txn_rate",
        ],
    },
    "refund_abuse": {
        "label": "Refund abuse",
        "model_path": _p("xgb_refund_abuse.json"),
        "threshold_path": _p("refund_threshold.pkl"),
        "cost_curve_path": _p("cost_curve_refund.json"),
        "feature_cols": [f"{c}_robust_z" for c in _REFUND_BASE] + [f"{c}_pct_change" for c in _REFUND_BASE],
    },
}

_DETECTORS = {}
for _name, _cfg in LOSS_CLASSES.items():
    if not (os.path.exists(_cfg["model_path"]) and os.path.exists(_cfg["threshold_path"])):
        print(f"[ml_pipeline] artifacts for '{_name}' not found, class disabled")
        continue
    _model = xgb.XGBClassifier()
    _model.load_model(_cfg["model_path"])
    _DETECTORS[_name] = {
        "model": _model,
        "explainer": shap.TreeExplainer(_model),
        "threshold": float(joblib.load(_cfg["threshold_path"])),
    }


def is_available(loss_class: str) -> bool:
    return loss_class in _DETECTORS


def get_threshold(loss_class: str) -> float:
    if not is_available(loss_class):
        raise ValueError(f"Loss class '{loss_class}' is not available")
    return _DETECTORS[loss_class]["threshold"]


def score_transaction(feature_dict: dict, loss_class: str = "txn_spike") -> dict:
    """Scores one merchant-day for a given loss class and returns the model score and top SHAP feature."""
    if not is_available(loss_class):
        raise ValueError(f"Loss class '{loss_class}' is not available")
    det = _DETECTORS[loss_class]
    cols = LOSS_CLASSES[loss_class]["feature_cols"]

    x = np.array([[feature_dict[c] for c in cols]], dtype=float)
    proba = float(det["model"].predict_proba(x)[0, 1])
    shap_vals = det["explainer"].shap_values(x)
    top_feature = cols[int(np.argmax(np.abs(shap_vals[0])))]

    return {
        "xgb_proba": proba,
        "shap_top_feature": top_feature,
        "should_investigate": proba >= det["threshold"],
    }


# Backward-compatible names used by the Phase 7 tests
FEATURE_COLS = LOSS_CLASSES["txn_spike"]["feature_cols"]
DECISION_THRESHOLD = get_threshold("txn_spike")