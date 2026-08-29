import { useState } from "react";
import MetricCard from "./MetricCard";
import CaseQueue from "./CaseQueue";
import CaseDetail from "./CaseDetail";

const DUMMY_CASES = [
  { case_id: 1, merchant_id: "M0142", xgb_proba: 0.91, decision: "ESCALATE_TO_HUMAN" },
  { case_id: 2, merchant_id: "M0077", xgb_proba: 0.74, decision: "REQUEST_VERIFICATION" },
  { case_id: 3, merchant_id: "M0203", xgb_proba: 0.58, decision: "MONITOR" },
];

const DUMMY_INVESTIGATIONS = {
  1: {
    case_id: 1, merchant_id: "M0142", day: 63, xgb_proba: 0.91, decision: "ESCALATE_TO_HUMAN",
    transaction_finding: "Transaction count is 6.1 standard deviations above the 14-day baseline, while average ticket size jumped 4.3x with fewer total transactions.",
    merchant_finding: "Refund rate is within normal range for this merchant; device count is stable, ruling out account takeover as a likely cause.",
    retrieved_policies: [{ id: "R-204", text: "Average ticket size anomaly combined with an electronics category merchant requires escalation to human review per policy." }],
  },
};

export default function Dashboard() {
  const [selectedId, setSelectedId] = useState(1);

  const summary = { flaggedToday: 37, highRisk: 9, pendingReview: 14, falsePositiveRate: "6.2%" };
  const investigation = DUMMY_INVESTIGATIONS[selectedId];

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "1.5rem" }}>
        <MetricCard label="Flagged today" value={summary.flaggedToday} />
        <MetricCard label="High risk" value={summary.highRisk} tone="danger" />
        <MetricCard label="Pending review" value={summary.pendingReview} tone="warning" />
        <MetricCard label="False positive rate" value={summary.falsePositiveRate} tone="success" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "220px minmax(0,1fr)", border: "0.5px solid var(--border)", borderRadius: "12px", overflow: "hidden" }}>
        <CaseQueue cases={DUMMY_CASES} selectedId={selectedId} onSelect={setSelectedId} />
        <CaseDetail
          investigation={investigation}
          onApprove={() => alert("Wire this to POST /investigations/:id/approve in Step 3")}
          onOverride={() => alert("Wire this to POST /investigations/:id/override in Step 3")}
        />
      </div>
    </div>
  );
}