const statusColor = {
  MONITOR: "var(--text-success)",
  REQUEST_VERIFICATION: "var(--text-warning)",
  ESCALATE_TO_HUMAN: "var(--text-danger)",
};

export default function CasesTable({ cases }) {
  return (
    <div style={{ background: "var(--surface-1)", border: "0.5px solid var(--border)", borderRadius: "12px", padding: "16px" }}>
      <p style={{ fontSize: "14px", fontWeight: 600, margin: "0 0 12px" }}>Recent cases</p>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
        <thead>
          <tr style={{ textAlign: "left", color: "var(--text-muted)" }}>
            <th style={{ padding: "6px 8px", fontWeight: 500 }}>Merchant</th>
            <th style={{ padding: "6px 8px", fontWeight: 500 }}>Score</th>
            <th style={{ padding: "6px 8px", fontWeight: 500 }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {cases.slice(0, 8).map((c) => (
            <tr key={c.case_id} style={{ borderTop: "0.5px solid var(--border)" }}>
              <td style={{ padding: "8px" }}>
                <span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: statusColor[c.decision], marginRight: "8px" }} />
                {c.merchant_id}
              </td>
              <td style={{ padding: "8px" }}>{c.xgb_proba.toFixed(2)}</td>
              <td style={{ padding: "8px", color: statusColor[c.decision] }}>{c.decision?.replace(/_/g, " ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}