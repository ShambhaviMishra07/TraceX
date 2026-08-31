export default function EvidenceCard({ icon, title, text }) {
  return (
    <div style={{ border: "0.5px solid var(--border)", borderRadius: "8px", padding: "10px 12px" }}>
      <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "0 0 4px" }}>
        <i className={`ti ${icon}`} style={{ fontSize: "14px", verticalAlign: "-2px", marginRight: "4px" }} aria-hidden="true" />
        {title}
      </p>
      <p style={{ fontSize: "13px", margin: 0 }}>{text}</p>
    </div>
  );
}