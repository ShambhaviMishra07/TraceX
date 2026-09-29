import pytest
from agent_pipeline import gate_node, route_after_gate, decision_agent, DECISION_THRESHOLD


def make_state(xgb_proba, **overrides):
    state = {
        "merchant_id": "M_TEST", "day": 1,
        "features": {}, "xgb_proba": xgb_proba,
        "shap_top_feature": "txn_count_robust_z",
        "should_investigate": False,
    }
    state.update(overrides)
    return state


# --- Gate logic ---

def test_gate_flags_score_above_threshold():
    state = gate_node(make_state(xgb_proba=DECISION_THRESHOLD + 0.1))
    assert state["should_investigate"] is True


def test_gate_does_not_flag_score_below_threshold():
    state = gate_node(make_state(xgb_proba=max(0.0, DECISION_THRESHOLD - 0.1)))
    assert state["should_investigate"] is False


def test_route_after_gate_investigate_path():
    state = make_state(xgb_proba=0.9, should_investigate=True)
    assert route_after_gate(state) == "investigate"


def test_route_after_gate_end_path():
    state = make_state(xgb_proba=0.01, should_investigate=False)
    assert route_after_gate(state) == "end_no_action"


# --- Decision agent: the deterministic score -> action mapping ---
# These are the rules that MUST stay correct — this is the part of the
# system explicitly designed to never be an LLM call.

def test_ambiguous_confidence_band_always_escalates():
    """Policy R-600: 0.4-0.7 confidence must never be auto-actioned."""
    for proba in [0.4, 0.55, 0.7]:
        state = decision_agent(make_state(xgb_proba=proba))
        assert state["decision"] == "ESCALATE_TO_HUMAN"


def test_very_high_confidence_escalates():
    state = decision_agent(make_state(xgb_proba=0.9))
    assert state["decision"] == "ESCALATE_TO_HUMAN"


def test_moderately_high_confidence_requests_verification():
    state = decision_agent(make_state(xgb_proba=0.75))
    assert state["decision"] == "REQUEST_VERIFICATION"


def test_low_confidence_monitors():
    state = decision_agent(make_state(xgb_proba=0.1))
    assert state["decision"] == "MONITOR"


def test_decision_confidence_matches_input_proba():
    state = decision_agent(make_state(xgb_proba=0.837))
    assert state["decision_confidence"] == 0.837