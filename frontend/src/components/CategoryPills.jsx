const PILLS = [
  { key: "all", label: "All Cases", bg: "var(--accent-blue)", text: "#fff" },
  { key: "MONITOR", label: "Monitor", bg: "var(--text-success)", text: "#062b13" },
  { key: "REQUEST_VERIFICATION", label: "Needs Verification", bg: "var(--text-warning)", text: "#3a2405" },
  { key: "ESCALATE_TO_HUMAN", label: "Needs Attention", bg: "var(--text-danger)", text: "#3a0a0a" },
];

export default function CategoryPills({ activeFilter, onFilterChange }) {
  return (
    <div style={{ display: "flex", gap: "10px", marginBottom: "1.25rem" }}>
      {PILLS.map((p) => (
        <button
          key={p.key}
          onClick={() => onFilterChange(p.key)}
          style={{
            background: p.bg,
            color: p.text,
            border: "none",
            padding: "10px 18px",
            borderRadius: "10px",
            fontSize: "13px",
            fontWeight: 600,
            opacity: activeFilter === p.key ? 1 : 0.55,
            transition: "opacity 0.12s ease",
          }}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}