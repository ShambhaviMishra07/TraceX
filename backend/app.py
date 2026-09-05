import json
import os

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv("backend/.env")

from backend.db import (
    init_db,
    get_db,
    Merchant,
    TransactionDay,
    RiskCase,
    Investigation,
)
from backend.schemas import (
    TransactionDayIn,
    InvestigationOut,
    DecisionOverrideIn,
)
from backend.ml_pipeline import score_transaction, FEATURE_COLS
from backend.agent_pipeline import run_investigation


app = FastAPI(title="Fraud-Spike Investigator API")


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

init_db()


# ============================================================
# TRANSACTIONS
# ============================================================

@app.post("/transactions")
def ingest_transaction(
    txn: TransactionDayIn,
    db: Session = Depends(get_db),
):
    merchant = (
        db.query(Merchant)
        .filter_by(merchant_id=txn.merchant_id)
        .first()
    )

    if not merchant:
        merchant = Merchant(
            merchant_id=txn.merchant_id,
            category=txn.category,
        )
        db.add(merchant)
        db.commit()

    raise HTTPException(
        status_code=501,
        detail=(
            "Feature computation requires merchant history — "
            "use /transactions/bulk-load for demo data."
        ),
    )


@app.post("/transactions/bulk-load")
def bulk_load(
    rows: list[dict],
    db: Session = Depends(get_db),
):
    """
    Accepts pre-featured rows from the Phase 1/2 notebook export,
    scores each row, and creates a RiskCase for anything the model flags.
    """

    created_cases = []

    for row in rows:

        # ----------------------------------------------------
        # Merchant
        # ----------------------------------------------------

        merchant = (
            db.query(Merchant)
            .filter_by(merchant_id=row["merchant_id"])
            .first()
        )

        if not merchant:
            merchant = Merchant(
                merchant_id=row["merchant_id"],
                category=row.get("category", "unknown"),
            )
            db.add(merchant)
            db.commit()

        # ----------------------------------------------------
        # Transaction snapshot
        # ----------------------------------------------------

        db.add(
            TransactionDay(
                merchant_id=row["merchant_id"],
                day=row["day"],
                txn_count=row["txn_count"],
                total_amount=row["total_amount"],
                refund_rate=row["refund_rate"],
                unique_devices=row["unique_devices"],
                failed_txn_rate=row["failed_txn_rate"],
                features={
                    col: row[col]
                    for col in FEATURE_COLS
                },
            )
        )

        # ----------------------------------------------------
        # ML scoring
        # ----------------------------------------------------

        score = score_transaction(
            {
                col: row[col]
                for col in FEATURE_COLS
            }
        )

        # ----------------------------------------------------
        # Create risk case if flagged
        # ----------------------------------------------------

        if score["should_investigate"]:

            case = RiskCase(
                merchant_id=row["merchant_id"],
                day=row["day"],
                xgb_proba=score["xgb_proba"],
                shap_top_feature=score["shap_top_feature"],
            )

            db.add(case)

            created_cases.append(
                row["merchant_id"]
            )

    db.commit()

    return {
        "loaded_rows": len(rows),
        "flagged_cases": len(created_cases),
    }


# ============================================================
# RISK CASES
# ============================================================

@app.get("/risk-cases")
def list_risk_cases(
    status: str = None,
    db: Session = Depends(get_db),
):
    """
    Lists flagged cases sorted by model score.

    Includes the current investigation decision.
    Returns None for cases that have not been investigated yet.
    """

    query = db.query(RiskCase)

    if status:
        query = query.filter_by(status=status)

    cases = (
        query
        .order_by(RiskCase.xgb_proba.desc())
        .all()
    )

    result = []

    for case in cases:

        result.append(
            {
                "case_id": case.id,
                "merchant_id": case.merchant_id,
                "day": case.day,
                "xgb_proba": case.xgb_proba,
                "status": case.status,
                "decision": (
                    case.investigation.decision
                    if case.investigation
                    else None
                ),
            }
        )

    return result


# ============================================================
# DASHBOARD — CASES BY DAY
# ============================================================

@app.get("/risk-dashboard/by-day")
def cases_by_day(
    db: Session = Depends(get_db),
):
    """
    Returns investigated case counts grouped by day and decision.
    """

    rows = (
        db.query(
            RiskCase.day,
            Investigation.decision,
            func.count(Investigation.id),
        )
        .join(
            Investigation,
            Investigation.case_id == RiskCase.id,
        )
        .group_by(
            RiskCase.day,
            Investigation.decision,
        )
        .all()
    )

    by_day = {}

    for day, decision, count in rows:

        if day not in by_day:
            by_day[day] = {
                "day": f"Day {day}",
                "monitor": 0,
                "verify": 0,
                "escalate": 0,
            }

        key = {
            "MONITOR": "monitor",
            "REQUEST_VERIFICATION": "verify",
            "ESCALATE_TO_HUMAN": "escalate",
        }.get(decision)

        if key:
            by_day[day][key] = count

    # Sort numerically by the actual day value
    return [
        by_day[day]
        for day in sorted(by_day.keys())
    ]


# ============================================================
# MODEL COST CURVE
# ============================================================

@app.get("/model/cost-curve")
def get_cost_curve():
    """
    Returns the precision/recall/cost tradeoff table
    exported from the Phase 2 notebook.
    """

    # Always resolve the file relative to backend/app.py
    path = os.path.join(
        os.path.dirname(__file__),
        "cost_curve.json",
    )

    try:

        with open(path, "r") as f:
            data = json.load(f)

        # Downsample for frontend
        return data[::5]

    except FileNotFoundError:

        raise HTTPException(
            status_code=404,
            detail=(
                "cost_curve.json not found. "
                "Place it inside the backend folder."
            ),
        )


# ============================================================
# INVESTIGATION — RUN
# ============================================================

@app.post(
    "/investigations/{case_id}/run",
    response_model=InvestigationOut,
)
def run_case_investigation(
    case_id: int,
    db: Session = Depends(get_db),
):
    """
    Runs the LangGraph investigation pipeline for a risk case.
    """

    # --------------------------------------------------------
    # Find case
    # --------------------------------------------------------

    case = (
        db.query(RiskCase)
        .filter_by(id=case_id)
        .first()
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found",
        )

    # --------------------------------------------------------
    # Find transaction feature snapshot
    # --------------------------------------------------------

    txn_day = (
        db.query(TransactionDay)
        .filter_by(
            merchant_id=case.merchant_id,
            day=case.day,
        )
        .first()
    )

    if not txn_day:
        raise HTTPException(
            status_code=400,
            detail="No feature snapshot found for this case",
        )

    # --------------------------------------------------------
    # Build investigation state
    # --------------------------------------------------------

    state = {
        "merchant_id": case.merchant_id,
        "day": case.day,
        "features": txn_day.features,
        "xgb_proba": case.xgb_proba,
        "shap_top_feature": case.shap_top_feature,
        "should_investigate": True,
    }

    # --------------------------------------------------------
    # Run agentic investigation
    # --------------------------------------------------------

    result = run_investigation(state)

    # --------------------------------------------------------
    # Save investigation
    # --------------------------------------------------------

    investigation = Investigation(
        case_id=case.id,
        transaction_finding=result["transaction_finding"],
        merchant_finding=result["merchant_finding"],
        retrieved_policies=result["retrieved_policies"],
        evidence_summary=result["evidence_summary"],
        decision=result["decision"],
        decision_confidence=result["decision_confidence"],
        explanation_matches_shap=result[
            "explanation_matches_shap"
        ],
    )

    db.add(investigation)

    # Mark case as investigated
    case.status = "INVESTIGATED"

    db.commit()
    db.refresh(investigation)

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "case_id": case.id,
        "merchant_id": case.merchant_id,
        "day": case.day,
        "xgb_proba": case.xgb_proba,
        **result,
    }


# ============================================================
# INVESTIGATION — GET EXISTING
# ============================================================

@app.get("/investigations/{case_id}")
def get_investigation(
    case_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns an already-completed investigation.

    Uses the same response shape as /run so the frontend
    can safely render both newly-created and existing investigations.
    """

    inv = (
        db.query(Investigation)
        .filter_by(case_id=case_id)
        .first()
    )

    if not inv:
        raise HTTPException(
            status_code=404,
            detail="No investigation found for this case yet",
        )

    case = (
        db.query(RiskCase)
        .filter_by(id=case_id)
        .first()
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found",
        )

    return {
        "case_id": case.id,
        "merchant_id": case.merchant_id,
        "day": case.day,
        "xgb_proba": case.xgb_proba,
        "transaction_finding": inv.transaction_finding,
        "merchant_finding": inv.merchant_finding,
        "retrieved_policies": inv.retrieved_policies,
        "evidence_summary": inv.evidence_summary,
        "decision": inv.decision,
        "decision_confidence": inv.decision_confidence,
        "explanation_matches_shap": inv.explanation_matches_shap,
    }


# ============================================================
# HUMAN REVIEW / OVERRIDE
# ============================================================

@app.post("/investigations/{case_id}/override")
def override_decision(
    case_id: int,
    override: DecisionOverrideIn,
    db: Session = Depends(get_db),
):
    """
    Records a human approval or override decision.
    """

    inv = (
        db.query(Investigation)
        .filter_by(case_id=case_id)
        .first()
    )

    if not inv:
        raise HTTPException(
            status_code=404,
            detail="No investigation found for this case",
        )

    inv.reviewed_by_human = True
    inv.human_override_decision = override.human_decision

    db.commit()

    return {
        "status": "updated",
        "case_id": case_id,
        "new_decision": override.human_decision,
    }


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

@app.get("/risk-dashboard/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
):
    """
    Returns summary metrics used by the dashboard.
    """

    total_cases = (
        db.query(RiskCase)
        .count()
    )

    investigated = (
        db.query(RiskCase)
        .filter_by(status="INVESTIGATED")
        .count()
    )

    high_risk = (
        db.query(Investigation)
        .filter(
            Investigation.decision.in_(
                [
                    "ESCALATE_TO_HUMAN",
                    "REQUEST_VERIFICATION",
                ]
            )
        )
        .count()
    )

    return {
        "total_flagged_cases": total_cases,
        "investigated": investigated,
        "pending": total_cases - investigated,
        "high_risk_decisions": high_risk,
    }