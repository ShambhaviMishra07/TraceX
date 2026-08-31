import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

const COLORS = { Monitor: "#4ade80", Verify: "#fbbf24", Escalate: "#f87171" };

export default function DecisionPieChart({ data }) {
  // expects data: [{ name: "Monitor", value: 61 }, { name: "Verify", value: 25 }, { name: "Escalate", value: 9 }]
  return (
    <div style={{ background: "var(--surface-1)", border: "0.5px solid var(--border)", borderRadius: "12px", padding: "16px" }}>
      <p style={{ fontSize: "14px", fontWeight: 600, margin: "0 0 12px" }}>Decision breakdown</p>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={3}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={COLORS[entry.name]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ background: "var(--surface-2)", border: "0.5px solid var(--border)", borderRadius: "8px", fontSize: "12px" }} />
          <Legend wrapperStyle={{ fontSize: "12px" }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}