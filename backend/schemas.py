from pydantic import BaseModel
from typing import Optional, List, Dict


class TransactionDayIn(BaseModel):
    merchant_id: str
    category: str
    day: int
    txn_count: float
    total_amount: float
    refund_rate: float
    unique_devices: float
    failed_txn_rate: float


class InvestigationOut(BaseModel):
    case_id: int
    merchant_id: str
    day: int
    xgb_proba: float
    transaction_finding: Optional[str]
    merchant_finding: Optional[str]
    retrieved_policies: Optional[List[Dict]]
    evidence_summary: Optional[str]
    decision: Optional[str]
    decision_confidence: Optional[float]
    explanation_matches_shap: Optional[bool]

    class Config:
        from_attributes = True


class DecisionOverrideIn(BaseModel):
    human_decision: str   # ALLOW, MONITOR, REQUEST_VERIFICATION, ESCALATE_TO_HUMAN, TEMPORARILY_HOLD
    reviewer_note: Optional[str] = None