import xgboost as xgb
import joblib
import numpy as np
import shap

FEATURE_COLS = [
    "txn_count_robust_z", "total_amount_robust_z",
    "refund_rate_robust_z", "unique_devices_robust_z",
    "txn_count_pct_change", "total_amount_pct_change",
    "refund_rate_pct_change", "unique_devices_pct_change",
    "failed_txn_rate",
]

model = xgb.XGBClassifier()
model.load_model("xgb_fraud_spike.json")
DECISION_THRESHOLD = joblib.load("decision_threshold.pkl")

explainer = shap.TreeExplainer(model)


def score_transaction(feature_dict: dict) -> dict:
    """Takes engineered features for one merchant-day, returns model score + top SHAP feature."""
    x = np.array([[feature_dict[col] for col in FEATURE_COLS]])
    proba = float(model.predict_proba(x)[0, 1])

    shap_vals = explainer.shap_values(x)
    top_feature = FEATURE_COLS[int(np.argmax(np.abs(shap_vals[0])))]

    return {
        "xgb_proba": proba,
        "shap_top_feature": top_feature,
        "should_investigate": proba >= DECISION_THRESHOLD,
    }