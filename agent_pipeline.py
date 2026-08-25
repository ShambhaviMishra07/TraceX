"""
agent_pipeline.py
LangGraph investigation pipeline: Transaction Pattern Agent, Merchant History
Agent, Policy RAG Agent, Evidence Agent, Decision Agent.

Explains a real XGBoost score/SHAP signal — never decides the score itself.
"""

import os
from typing import TypedDict, Optional
from getpass import getpass

import chromadb
from chromadb.utils import embedding_functions
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END


# ── API key ──────────────────────────────────────────────────────────
# Prefer an environment variable (set this in your shell / .env before
# running uvicorn) over prompting — getpass blocks server startup.
if "ANTHROPIC_API_KEY" not in os.environ:
    os.environ["ANTHROPIC_API_KEY"] = getpass("Enter your Anthropic API key: ")

llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)


# ── Decision threshold (must match Phase 2's cost-optimal threshold) ──
# Import from ml_pipeline so there's a single source of truth instead of
# a second hardcoded number drifting out of sync.
from ml_pipeline import DECISION_THRESHOLD


# ── Policy knowledge base ──────────────────────────────────────────────
policy_documents = [
    {
        "id": "R-101",
        "title": "Transaction Velocity Threshold",
        "text": "Policy R-101: If a merchant's daily transaction count exceeds 3x their trailing 14-day median with no prior notice of a promotional campaign, the account should be flagged for MONITOR status. If velocity exceeds 5x, escalate to REQUEST_VERIFICATION. Sustained velocity spikes over 3 consecutive days without merchant-declared cause should be escalated to a human investigator regardless of amount."
    },
    {
        "id": "R-204",
        "title": "Average Ticket Size Anomaly",
        "text": "Policy R-204: A sudden increase in average transaction value exceeding 4x the merchant's 30-day baseline, combined with a decrease in transaction count, is a known indicator of card-testing or high-value fraud rings. This pattern requires REQUEST_VERIFICATION at minimum. If the merchant category is electronics or travel, escalate directly to human review due to higher historical fraud correlation in these categories."
    },
    {
        "id": "R-310",
        "title": "Refund Rate Escalation",
        "text": "Policy R-310: A refund rate exceeding 15% of daily transaction volume, or a refund rate more than 3x the merchant's historical average, should trigger MONITOR status. If refund rate exceeds 30%, this may indicate a compromised merchant account or first-party fraud and should be escalated to human review."
    },
    {
        "id": "R-415",
        "title": "Device and IP Fan-Out",
        "text": "Policy R-415: A sudden increase in unique devices or IP addresses transacting through a merchant, exceeding 2.5x baseline within a 24-hour window, may indicate account takeover, credential stuffing, or a bot-driven abuse pattern. Combined with velocity spike, this should be treated as HIGH RISK and escalated regardless of transaction amount."
    },
    {
        "id": "R-500",
        "title": "Seasonal and Promotional Exemptions",
        "text": "Policy R-500: Merchants who have pre-registered a promotional campaign, sale event, or seasonal spike (e.g., festival sales) with the risk team are exempt from velocity and amount-based auto-escalation for the declared window, but remain subject to refund rate and device fan-out monitoring. Undeclared spikes matching promotional patterns should still be flagged for MONITOR, not immediate escalation, pending merchant contact."
    },
    {
        "id": "R-600",
        "title": "Confidence and Human Review Threshold",
        "text": "Policy R-600: Any case where the model confidence score falls between 0.4 and 0.7 (ambiguous zone) should not be auto-actioned. These cases require human review regardless of which other policies matched, since automated action in this confidence band has historically produced the highest false-positive cost."
    },
]

_chroma_client = chromadb.Client()
_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Guard against re-creating the collection on every hot-reload (uvicorn --reload
# re-imports this module) — Chroma raises if the collection already exists.
try:
    policy_collection = _chroma_client.create_collection(
        name="risk_policies", embedding_function=_embedding_fn
    )
    policy_collection.add(
        ids=[p["id"] for p in policy_documents],
        documents=[p["text"] for p in policy_documents],
        metadatas=[{"title": p["title"]} for p in policy_documents],
    )
except Exception:
    policy_collection = _chroma_client.get_collection(
        name="risk_policies", embedding_function=_embedding_fn
    )


# ── Shared state ────────────────────────────────────────────────────
class InvestigationState(TypedDict):
    merchant_id: str
    day: int
    features: dict
    xgb_proba: float
    shap_top_feature: str
    should_investigate: bool

    transaction_finding: Optional[str]
    merchant_finding: Optional[str]
    retrieved_policies: Optional[list]

    evidence_summary: Optional[str]
    decision: Optional[str]
    decision_confidence: Optional[float]
    explanation_matches_shap: Optional[bool]


# ── Nodes ────────────────────────────────────────────────────────────
def gate_node(state: InvestigationState) -> InvestigationState:
    state["should_investigate"] = state["xgb_proba"] >= DECISION_THRESHOLD
    return state


def route_after_gate(state: InvestigationState) -> str:
    return "investigate" if state["should_investigate"] else "end_no_action"


def transaction_pattern_agent(state: InvestigationState) -> InvestigationState:
    f = state["features"]
    prompt = f"""You are a transaction pattern analyst. Given these feature values for merchant {state['merchant_id']} on day {state['day']}, describe ONLY what the numbers show — no speculation about intent.

txn_count_robust_z: {f['txn_count_robust_z']:.2f}
total_amount_robust_z: {f['total_amount_robust_z']:.2f}
txn_count_pct_change: {f['txn_count_pct_change']:.2%}
total_amount_pct_change: {f['total_amount_pct_change']:.2%}
failed_txn_rate: {f['failed_txn_rate']:.2%}

Write 1-2 sentences stating the most significant deviation(s) in plain terms. Reference the actual numbers."""

    response = llm.invoke(prompt)
    state["transaction_finding"] = response.content
    return state


def merchant_history_agent(state: InvestigationState) -> InvestigationState:
    f = state["features"]
    prompt = f"""You are a merchant risk analyst. Compare merchant {state['merchant_id']}'s current behavior to its own historical baseline using these values:

refund_rate_robust_z: {f['refund_rate_robust_z']:.2f}
unique_devices_robust_z: {f['unique_devices_robust_z']:.2f}
refund_rate_pct_change: {f['refund_rate_pct_change']:.2%}
unique_devices_pct_change: {f['unique_devices_pct_change']:.2%}

In 1-2 sentences, state whether this merchant's refund and device patterns are within normal range for THIS merchant, or deviating — and by how much, using the numbers given."""

    response = llm.invoke(prompt)
    state["merchant_finding"] = response.content
    return state


def policy_agent(state: InvestigationState) -> InvestigationState:
    query_text = f"{state['transaction_finding']} {state['merchant_finding']}"
    results = policy_collection.query(query_texts=[query_text], n_results=2)

    retrieved = [
        {"id": pid, "title": meta["title"], "text": doc}
        for pid, doc, meta in zip(
            results["ids"][0], results["documents"][0], results["metadatas"][0]
        )
    ]
    state["retrieved_policies"] = retrieved
    return state


def evidence_agent(state: InvestigationState) -> InvestigationState:
    policies_text = "\n".join(
        [f"- {p['id']} ({p['title']}): {p['text']}" for p in state["retrieved_policies"]]
    )

    prompt = f"""Merge the following findings into a single evidence summary for merchant {state['merchant_id']}.

Transaction finding: {state['transaction_finding']}
Merchant history finding: {state['merchant_finding']}
Model anomaly score: {state['xgb_proba']:.2f}

Relevant policies:
{policies_text}

Write a 2-3 sentence evidence summary explaining WHY this merchant is flagged, citing the most relevant policy ID. Be specific, not generic."""

    response = llm.invoke(prompt)
    state["evidence_summary"] = response.content

    feature_keywords = {
        "txn_count_robust_z": ["transaction count", "velocity", "txn count"],
        "total_amount_robust_z": ["amount", "value", "ticket"],
        "refund_rate_robust_z": ["refund"],
        "unique_devices_robust_z": ["device"],
    }
    keywords = feature_keywords.get(state["shap_top_feature"], [])
    state["explanation_matches_shap"] = any(
        kw in response.content.lower() for kw in keywords
    )

    return state


def decision_agent(state: InvestigationState) -> InvestigationState:
    proba = state["xgb_proba"]

    if 0.4 <= proba <= 0.7:
        decision = "ESCALATE_TO_HUMAN"   # R-600: ambiguous zone, never auto-action
    elif proba > 0.85:
        decision = "ESCALATE_TO_HUMAN"
    elif proba > 0.7:
        decision = "REQUEST_VERIFICATION"
    else:
        decision = "MONITOR"

    state["decision"] = decision
    state["decision_confidence"] = round(float(proba), 3)
    return state


# ── Graph wiring ────────────────────────────────────────────────────
_graph = StateGraph(InvestigationState)

_graph.add_node("gate", gate_node)
_graph.add_node("transaction_agent", transaction_pattern_agent)
_graph.add_node("merchant_agent", merchant_history_agent)
_graph.add_node("policy_agent", policy_agent)
_graph.add_node("evidence_agent", evidence_agent)
_graph.add_node("decision_agent", decision_agent)

_graph.set_entry_point("gate")
_graph.add_conditional_edges("gate", route_after_gate, {
    "investigate": "transaction_agent",
    "end_no_action": END,
})

_graph.add_edge("transaction_agent", "merchant_agent")
_graph.add_edge("merchant_agent", "policy_agent")
_graph.add_edge("policy_agent", "evidence_agent")
_graph.add_edge("evidence_agent", "decision_agent")
_graph.add_edge("decision_agent", END)

investigation_app = _graph.compile()


# ── Public entry point used by app.py ──────────────────────────────
def run_investigation(state: dict) -> dict:
    return investigation_app.invoke(state)
