import { useState, useEffect, useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from "recharts";

const API_BASE = "http://localhost:8000";

export default function CostCurveSlider() {
  const [curve, setCurve] = useState([]);
  const [thresholdIdx, setThresholdIdx] = useState(0);

  useEffect(() => {
    fetch(`${API_BASE}/model/cost-curve`)
      .then((r) => r.json())
      .then((data) => {
        setCurve(data);
        // default to the cost-minimizing point
        const minIdx = data.reduce((best, row, i) => (row.total_cost < data[best].total_cost ? i : best), 0);
        setThresholdIdx(minIdx);
      });
  }, []);

  const current = curve[thresholdIdx];

  const chartData = useMemo(
    () => curve.map((row, i) => ({ idx: i, threshold: row.threshold, precision: row.precision, recall: row.recall })),
    [curve]
  );

  if (!curve.length) return null;

  return (
    <div style={{ background: "var(--surface-1)", border: "0.5px solid var(--border)", borderRadius: "12px", padding: "16px" }}>
      <p style={{ fontSize: "14px", fontWeight: 600, margin: "0 0 4px" }}>Threshold tradeoff explorer</p>
      <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "0 0 14px" }}>
        Drag to see how the detection threshold trades precision for recall and changes total review cost.
      </p>

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="threshold" stroke="var(--text-muted)" fontSize={11} tickFormatter={(v) => v.toFixed(2)} />
          <YAxis stroke="var(--text-muted)" fontSize={11} domain={[0, 1]} />
          <Tooltip contentStyle={{ background: "var(--surface-2)", border: "0.5px solid var(--border)", borderRadius: "8px", fontSize: "12px" }} />
          <Line type="monotone" dataKey="precision" stroke="var(--accent-blue)" dot={false} strokeWidth={2} name="Precision" />
          <Line type="monotone" dataKey="recall" stroke="var(--text-success)" dot={false} strokeWidth={2} name="Recall" />
          <ReferenceLine x={current?.threshold} stroke="var(--text-warning)" strokeDasharray="4 4" />
        </LineChart>
      </ResponsiveContainer>

      <input
        type="range"
        min={0}
        max={curve.length - 1}
        value={thresholdIdx}
        onChange={(e) => setThresholdIdx(Number(e.target.value))}
        style={{ width: "100%", marginTop: "12px" }}
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px", marginTop: "14px" }}>
        <StatBox label="Threshold" value={current.threshold.toFixed(2)} />
        <StatBox label="Precision" value={current.precision.toFixed(2)} />
        <StatBox label="Recall" value={current.recall.toFixed(2)} />
        <StatBox label="False positives" value={current.fp} tone="warning" />
      </div>
    </div>
  );
}

function StatBox({ label, value, tone }) {
  const color = tone === "warning" ? "var(--text-warning)" : "var(--text-primary)";
  return (
    <div style={{ textAlign: "center" }}>
      <p style={{ fontSize: "11px", color: "var(--text-muted)", margin: "0 0 2px" }}>{label}</p>
      <p style={{ fontSize: "16px", fontWeight: 600, margin: 0, color }}>{value}</p>
    </div>
  );
}