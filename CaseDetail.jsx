import EvidenceCard from "./EvidenceCard";

const decisionBadge = {
  ESCALATE_TO_HUMAN: { label: "Escalate to human", bg: "var(--bg-danger)", color: "var(--text-danger)" },
  REQUEST_VERIFICATION: { label: "Request verification", bg: "var(--bg-warning)", color: "var(--text-warning)" },
  MONITOR: { label: "Monitor", bg: "var(--surface-1)", color: "var(--text-secondary)" },
};

export default function CaseDetail({ investigation, onApprove, onOverride }) {
  if (!investigation) {
    return (
      <div style={{ padding: "20px", color: "var(--text-muted)", fontSize: "14px" }}>
        Select a case from the queue to see its investigation.
      </div>
    );
  }

  const badge = decisionBadge[investigation.decision] || decisionBadge.MONITOR;

  return (
    <div style={{ padding: "16px 20px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
        <div>
          <p style={{ fontSize: "15px", fontWeight: 500, margin: 0 }}>
            Merchant {investigation.merchant_id}
          </p>
          <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "2px 0 0" }}>
            Day {investigation.day} · model score {investigation.xgb_proba.toFixed(2)}
          </p>
        </div>
        <span style={{ background: badge.bg, color: badge.color, fontSize: "12px", padding: "4px 10px", borderRadius: "8px" }}>
          {badge.label}
        </span>
      </div>

      <div style={{ display: "grid", gap: "10px" }}>
        <EvidenceCard icon="ti-chart-bar" title="Transaction pattern agent" text={investigation.transaction_finding} />
        <EvidenceCard icon="ti-building-store" title="Merchant history agent" text={investigation.merchant_finding} />
        {investigation.retrieved_policies?.map((p) => (
          <EvidenceCard key={p.id} icon="ti-file-text" title={`Policy match · ${p.id}`} text={p.text} />
        ))}
      </div>

      <div style={{ display: "flex", gap: "8px", marginTop: "14px" }}>
        <button onClick={onApprove}>Approve decision</button>
        <button onClick={onOverride}>Override</button>
      </div>
    </div>
  );
}