# TraceX

> An AI-native merchant risk investigation system with real ML-based fraud-spike detection, a multi-agent explanation layer, and policy-grounded decisions.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-black?logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-ML%20Model-EB5E28?logo=xgboost&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20Orchestration-1C3C3C)
![Claude](https://img.shields.io/badge/Claude-Haiku%204.5-D97757?logo=anthropic&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-FF6B6B)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)

Instead of assigning a black-box risk score, this system detects abnormal merchant transaction spikes with a real, evaluated ML model, then runs a lightweight multi-agent investigation layer that explains *why* a merchant was flagged, citing the specific internal policy that applies — producing an auditable, explainable decision rather than an opaque number.

---

## Problem Statement

Payment platforms process millions of transactions across thousands of merchants. Risk teams need to catch abnormal merchant behavior — sudden transaction spikes, unusual ticket sizes, refund surges, device fan-out — early enough to act, without drowning analysts in false positives.

Most fraud-detection demos either (a) output a bare risk score with no explanation, or (b) wrap an LLM around raw data and let it "decide" risk with no real detection model underneath, no measured accuracy, and no accountability for being wrong.

**This project scopes to one loss class — merchant transaction-velocity/amount spikes — and treats the evaluation as the deliverable, not an afterthought.** The system:
- Detects anomalies with a trained, evaluated ML model (not an LLM)
- Investigates *why* a flagged case looks risky using a small set of specialized agents
- Cites the specific internal policy driving each decision (RAG-based)
- Reports honest precision/recall and false-positive cost — including how often it wrongly flags legitimate spikes like flash sales

## Why This Approach

A key design principle throughout: **the LLM explains, it never decides.** Every score, threshold, and action mapping is deterministic code. Agents narrate real feature values and real SHAP attributions — they don't generate risk assessments from scratch. This keeps the system auditable and prevents hallucinated reasoning from driving financial decisions.

## System Architecture

```
Synthetic Transaction Data (per-merchant daily aggregates)
        ↓
Feature Engineering (rolling robust z-scores, % change, merchant-relative baselines)
        ↓
ML Detector (Isolation Forest baseline + XGBoost classifier, SHAP explainability)
        ↓
Should Investigate? (cost-optimal threshold gate)
   ├─ NO  → logged, no action
   └─ YES ↓
   LangGraph Orchestrator
        ├─ Transaction Pattern Agent   — narrates velocity/amount signal from real features
        ├─ Merchant History Agent      — compares today vs. this merchant's own baseline
        └─ Policy Agent (RAG)          — retrieves matching internal policy, zero LLM calls
        ↓
   Evidence Agent — merges findings, cites policy, checked against SHAP ground truth
        ↓
   Decision Agent — deterministic mapping: (score, policy) → ALLOW / MONITOR /
                     REQUEST_VERIFICATION / ESCALATE_TO_HUMAN
        ↓
FastAPI backend — case logging, human override endpoint, dashboard summary API
        ↓
React dashboard — case queue + evidence panel (risk-analyst tool, not a chatbot)
```

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| ML detection | scikit-learn (Isolation Forest), XGBoost, SHAP | Explainable, fast to train, industry-standard for tabular anomaly/fraud detection |
| Agent orchestration | LangGraph + Claude (Haiku) | Structured, short, evidence-grounded reasoning — not long-form generation, so a fast/cheap model is the right fit |
| Policy retrieval | ChromaDB + sentence-transformers (`all-MiniLM-L6-v2`) | Local embeddings, zero API cost for retrieval, fast to stand up |
| Backend | FastAPI + SQLAlchemy + SQLite | Lightweight, zero-ops persistence appropriate for project scope |
| Frontend | React (Vite) | Fast iteration, component-based, matches a dense analyst-tool UI |

## ML Detection Layer

- **Synthetic dataset**: ~200 merchants × 90 days, with labeled anomalies (velocity spike, amount spike, refund spike, device fan-out) injected at varying severity, *plus* unlabeled benign spikes (flash sales, seasonal demand) to make false-positive evaluation meaningful rather than trivial.
- **Feature engineering**: rolling 14-day robust z-scores (median + MAD) and day-over-day % change per merchant, computed with no future leakage (`shift(1)` on all rolling windows).
- **Baseline detector**: robust z-score thresholding — zero training required, first sanity-check numbers.
- **Primary detector**: Isolation Forest (unsupervised, multivariate) and XGBoost (supervised, trained on labeled synthetic anomalies), evaluated on held-out **merchants** (not just held-out days) to test generalization, not memorization.
- **Threshold selection**: chosen via an explicit cost curve — false-positive cost (analyst review time) vs. false-negative cost (undetected loss) — rather than an arbitrary 0.5 cutoff.

## Agent Investigation Layer

Three narrow agents plus an Evidence and Decision agent, orchestrated with LangGraph:

- **Transaction Pattern Agent** — describes the velocity/amount deviation using the actual feature values for that merchant-day.
- **Merchant History Agent** — compares current behavior to that specific merchant's own baseline.
- **Policy Agent** — pure retrieval (no LLM call) against a small RAG corpus of internal risk policies (velocity thresholds, refund-rate escalation, device fan-out, promotional exemptions, confidence-band review rules).
- **Evidence Agent** — merges findings into a cited explanation, and is checked against the model's actual SHAP top feature to produce a measured **explanation accuracy** metric.
- **Decision Agent** — deterministic score → action mapping (never an LLM decision).

## Backend API

Key endpoints:

| Endpoint | Purpose |
|---|---|
| `POST /transactions/bulk-load` | Load pre-featured transaction rows, scores each with the ML model, creates a `RiskCase` for anything flagged |
| `GET /risk-cases` | List flagged cases, sorted by score |
| `POST /investigations/{case_id}/run` | Runs the LangGraph investigation for a case, persists the result |
| `GET /investigations/{case_id}` | Fetch a completed investigation |
| `POST /investigations/{case_id}/override` | Human-in-the-loop override of the system's decision |
| `GET /risk-dashboard/summary` | Aggregate metrics for the dashboard header |

Cases are flagged cheaply by the ML model at ingestion time; the (comparatively expensive, LLM-calling) investigation only runs on-demand for flagged cases — a deliberate cost-control decision.

## Frontend Dashboard

A dense, dark-mode analyst tool (not a chatbot UI): metric cards for flagged/high-risk/pending/false-positive-rate, a scannable case queue on the left, and an evidence panel on the right showing each agent's finding as a structured card, with the cited policy and a human approve/override action.

## Evaluation Methodology & Results


| Model | Precision | Recall | F1 | PR-AUC |
|---|---|---|---|---|
| Robust Z-Score Baseline | — | — | — | — |
| Isolation Forest | — | — | — | — |
| XGBoost (cost-optimal threshold) | — | — | — | — |

- **False-positive cost analysis**: at the chosen threshold, X false positives per Y true positives, translating to an estimated analyst review load of Z cases/day.
- **Benign-spike false positive rate**: of N legitimate spike days (flash sales, seasonal demand) in the test set, the final model incorrectly flagged M of them — the key evidence that the system distinguishes real risk from ordinary demand variation.
- **Explanation accuracy**: the agent layer's stated reasoning matched the model's actual top SHAP feature in X% of investigated cases.

## Project Structure

```
fraud-spike-investigator/
├── app.py                  # FastAPI app + routes
├── db.py                    # SQLAlchemy models + session
├── schemas.py                 # Pydantic request/response models
├── ml_pipeline.py               # Loads trained XGBoost model + scoring logic
├── agent_pipeline.py              # LangGraph investigation graph + policy RAG
├── xgb_fraud_spike.json             # Trained model (exported from notebook)
├── decision_threshold.pkl             # Cost-optimal decision threshold
├── requirements.txt
└── frontend/
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── Dashboard.jsx
        ├── theme.css
        └── components/
            ├── MetricCard.jsx
            ├── CaseQueue.jsx
            ├── CaseDetail.jsx
            └── EvidenceCard.jsx
```

## Setup & Running Locally

**Backend:**
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
uvicorn app:app --reload --port 8000
```
API docs available at `http://localhost:8000/docs`.

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Model training** (Colab notebook, run once, export artifacts):
1. Generate synthetic data
2. Engineer features
3. Train Isolation Forest + XGBoost, evaluate on held-out merchants
4. Export `xgb_fraud_spike.json` and `decision_threshold.pkl`, place next to `app.py`

## What's In Scope vs. Deliberately Out of Scope

**In scope:** one loss class (transaction-velocity/amount spikes), real evaluated detection, a narrow 5-agent investigation layer, policy RAG, human-review override, a working dashboard.

**Deliberately out of scope** (designed but not built, to protect depth over breadth within the project timeline): graph/network fraud-ring analysis across merchants/devices, a second loss class (e.g., refund-rate spikes) on the same pipeline, full analyst case-management workflow (assignment, SLA tracking), parallel agent execution.

## Security & Reliability Considerations

- **No offense-capable output**: the system only classifies and explains risk; it does not generate fraud techniques or evasion guidance.
- **Deterministic decisions**: the LLM layer never sets the risk score or chooses the action — both come from the trained model and fixed business rules, limiting the blast radius of any single hallucinated agent response.
- **Ambiguous-confidence handling**: cases in the 0.4–0.7 model-confidence band are never auto-actioned; they route to human review by policy (R-600).
- **Explanation grounding check**: each Evidence Agent output is checked against the model's actual SHAP top feature, catching cases where the narrated reasoning has drifted from what the model actually detected.