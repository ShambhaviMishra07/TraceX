from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from backend.db import init_db, get_db, Merchant, TransactionDay, RiskCase, Investigation
from backend.schemas import TransactionDayIn, InvestigationOut, DecisionOverrideIn
from backend.ml_pipeline import score_transaction, FEATURE_COLS
from backend.agent_pipeline import run_investigation

app = FastAPI(title="Fraud-Spike Investigator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default dev port
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.post("/transactions")
def ingest_transaction(txn: TransactionDayIn, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter_by(merchant_id=txn.merchant_id).first()
    if not merchant:
        merchant = Merchant(merchant_id=txn.merchant_id, category=txn.category)
        db.add(merchant)
        db.commit()

    # NOTE: in production this would look up rolling history and compute real
    # features. For the MVP, pass pre-computed features from your notebook pipeline.
    raise HTTPException(
        status_code=501,
        detail="Feature computation requires merchant history — use /transactions/bulk-load for demo data."
    )


@app.post("/transactions/bulk-load")
def bulk_load(rows: list[dict], db: Session = Depends(get_db)):
    """
    Accepts pre-featured rows (from your Phase 1/2 notebook export) and scores
    each one, creating a RiskCase for anything the model flags.
    """
    created_cases = []
    for row in rows:
        merchant = db.query(Merchant).filter_by(merchant_id=row["merchant_id"]).first()
        if not merchant:
            merchant = Merchant(merchant_id=row["merchant_id"], category=row.get("category", "unknown"))
            db.add(merchant)
            db.commit()

        db.add(TransactionDay(
            merchant_id=row["merchant_id"], day=row["day"],
            txn_count=row["txn_count"], total_amount=row["total_amount"],
            refund_rate=row["refund_rate"], unique_devices=row["unique_devices"],
            failed_txn_rate=row["failed_txn_rate"],
            features={col: row[col] for col in FEATURE_COLS},
        ))

        score = score_transaction({col: row[col] for col in FEATURE_COLS})
        if score["should_investigate"]:
            case = RiskCase(
                merchant_id=row["merchant_id"], day=row["day"],
                xgb_proba=score["xgb_proba"], shap_top_feature=score["shap_top_feature"],
            )
            db.add(case)
            created_cases.append(row["merchant_id"])

    db.commit()
    return {"loaded_rows": len(rows), "flagged_cases": len(created_cases)}


@app.get("/risk-cases")
def list_risk_cases(status: str = None, db: Session = Depends(get_db)):
    query = db.query(RiskCase)
    if status:
        query = query.filter_by(status=status)
    cases = query.order_by(RiskCase.xgb_proba.desc()).all()
    return [
        {"case_id": c.id, "merchant_id": c.merchant_id, "day": c.day,
         "xgb_proba": c.xgb_proba, "status": c.status}
        for c in cases
    ]


@app.post("/investigations/{case_id}/run", response_model=InvestigationOut)
def run_case_investigation(case_id: int, db: Session = Depends(get_db)):
    case = db.query(RiskCase).filter_by(id=case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    txn_day = db.query(TransactionDay).filter_by(
        merchant_id=case.merchant_id, day=case.day
    ).first()
    if not txn_day:
        raise HTTPException(400, "No feature snapshot found for this case")

    state = {
        "merchant_id": case.merchant_id, "day": case.day,
        "features": txn_day.features,
        "xgb_proba": case.xgb_proba, "shap_top_feature": case.shap_top_feature,
        "should_investigate": True,
    }
    result = run_investigation(state)

    investigation = Investigation(
        case_id=case.id,
        transaction_finding=result["transaction_finding"],
        merchant_finding=result["merchant_finding"],
        retrieved_policies=result["retrieved_policies"],
        evidence_summary=result["evidence_summary"],
        decision=result["decision"],
        decision_confidence=result["decision_confidence"],
        explanation_matches_shap=result["explanation_matches_shap"],
    )
    db.add(investigation)
    case.status = "INVESTIGATED"
    db.commit()
    db.refresh(investigation)

    return {
        "case_id": case.id, "merchant_id": case.merchant_id, "day": case.day,
        "xgb_proba": case.xgb_proba, **result,
    }


@app.get("/investigations/{case_id}")
def get_investigation(case_id: int, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter_by(case_id=case_id).first()
    if not inv:
        raise HTTPException(404, "No investigation found for this case yet")
    return inv


@app.post("/investigations/{case_id}/override")
def override_decision(case_id: int, override: DecisionOverrideIn, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter_by(case_id=case_id).first()
    if not inv:
        raise HTTPException(404, "No investigation found for this case")
    inv.reviewed_by_human = True
    inv.human_override_decision = override.human_decision
    db.commit()
    return {"status": "updated", "case_id": case_id, "new_decision": override.human_decision}


@app.get("/risk-dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total_cases = db.query(RiskCase).count()
    investigated = db.query(RiskCase).filter_by(status="INVESTIGATED").count()
    high_risk = db.query(Investigation).filter(
        Investigation.decision.in_(["ESCALATE_TO_HUMAN", "REQUEST_VERIFICATION"])
    ).count()

    return {
        "total_flagged_cases": total_cases,
        "investigated": investigated,
        "pending": total_cases - investigated,
        "high_risk_decisions": high_risk,
    }

@app.get("/risk-dashboard/by-day")
def cases_by_day(db: Session = Depends(get_db)):
    from sqlalchemy import func

    rows = db.query(
        RiskCase.day,
        Investigation.decision,
        func.count(Investigation.id)
    ).join(
        Investigation,
        Investigation.case_id == RiskCase.id
    ).group_by(
        RiskCase.day,
        Investigation.decision
    ).all()

    by_day = {}

    for day, decision, count in rows:
        by_day.setdefault(
            day,
            {
                "day": f"Day {day}",
                "monitor": 0,
                "verify": 0,
                "escalate": 0
            }
        )

        key = {
            "MONITOR": "monitor",
            "REQUEST_VERIFICATION": "verify",
            "ESCALATE_TO_HUMAN": "escalate"
        }.get(decision)

        if key:
            by_day[day][key] = count

    return sorted(by_day.values(), key=lambda x: x["day"])