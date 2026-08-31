export default function MetricCard({ label, value, tone = "default" }) {
  const toneColors = {
    default: "var(--text-primary)",
    danger: "var(--text-danger)",
    warning: "var(--text-warning)",
    success: "var(--text-success)",
  };

  return (
    <div
      className="metric-card"
      style={{
        background: "var(--surface-1)",
        borderRadius: "8px",
        padding: "1rem",
      }}
    >
      <p
        style={{
          fontSize: "13px",
          color: "var(--text-secondary)",
          margin: "0 0 4px",
        }}
      >
        {label}
      </p>

      <p
        style={{
          fontSize: "24px",
          fontWeight: 500,
          margin: 0,
          color: toneColors[tone],
        }}
      >
        {value}
      </p>
    </div>
  );
}