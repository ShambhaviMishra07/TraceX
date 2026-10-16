const TABS = [
  { key: "txn_spike", label: "Transaction spikes" },
  { key: "refund_abuse", label: "Refund abuse" },
];

export default function LossClassTabs({ active, onChange }) {
  return (
    <div style={{ display: "flex", gap: "4px", borderBottom: "0.5px solid var(--border)", marginBottom: "1.25rem" }}>
      {TABS.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          style={{
            background: "transparent",
            border: "none",
            borderBottom: active === t.key ? "2px solid var(--accent-blue)" : "2px solid transparent",
            borderRadius: 0,
            color: active === t.key ? "var(--text-primary)" : "var(--text-muted)",
            fontWeight: active === t.key ? 600 : 400,
            padding: "10px 16px",
            fontSize: "14px",
          }}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}