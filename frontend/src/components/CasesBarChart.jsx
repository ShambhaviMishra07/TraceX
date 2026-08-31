import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from "recharts";

export default function CasesBarChart({ data }) {
  // expects data: [{ day: "17 Feb", monitor: 12, verify: 5, escalate: 2 }, ...]
  return (
    <div style={{ background: "var(--surface-1)", border: "0.5px solid var(--border)", borderRadius: "12px", padding: "16px" }}>
      <p style={{ fontSize: "14px", fontWeight: 600, margin: "0 0 12px" }}>Cases by day</p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="day" stroke="var(--text-muted)" fontSize={12} />
          <YAxis stroke="var(--text-muted)" fontSize={12} />
          <Tooltip contentStyle={{ background: "var(--surface-2)", border: "0.5px solid var(--border)", borderRadius: "8px", fontSize: "12px" }} />
          <Legend wrapperStyle={{ fontSize: "12px" }} />
          <Bar dataKey="monitor" name="Monitor" fill="var(--text-success)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="verify" name="Verify" fill="var(--text-warning)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="escalate" name="Escalate" fill="var(--text-danger)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}