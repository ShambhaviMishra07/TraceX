const decisionTone = {
  ESCALATE_TO_HUMAN: { label: "Escalate", color: "var(--text-danger)" },
  REQUEST_VERIFICATION: { label: "Verify", color: "var(--text-warning)" },
  MONITOR: { label: "Monitor", color: "var(--text-secondary)" },
};

export default function CaseQueue({ cases, selectedId, onSelect }) {
  return (
    <div style={{ borderRight: "0.5px solid var(--border)" }}>
      <div style={{ padding: "10px 14px", fontSize: "12px", color: "var(--text-muted)", borderBottom: "0.5px solid var(--border)" }}>
        Case queue
      </div>
      {cases.map((c) => {
        const tone = decisionTone[c.decision] || decisionTone.MONITOR;
        const isSelected = c.case_id === selectedId;
        return (
          <div
            key={c.case_id}
            onClick={() => onSelect(c.case_id)}
            style={{
              padding: "12px 14px",
              borderBottom: "0.5px solid var(--border)",
              background: isSelected ? "var(--fill-ghost-selected)" : "transparent",
              cursor: "pointer",
            }}
          >
            <p style={{ fontSize: "13px", fontWeight: 500, margin: 0 }}>{c.merchant_id}</p>
            <p style={{ fontSize: "12px", color: tone.color, margin: "2px 0 0" }}>
              Score {c.xgb_proba.toFixed(2)} · {tone.label}
            </p>
          </div>
        );
      })}
    </div>
  );
}