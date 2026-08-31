import { useState, useEffect, useMemo } from "react";
import MetricCard from "./components/MetricCard";
import CaseQueue from "./components/CaseQueue";
import CaseDetail from "./components/CaseDetail";
import CategoryPills from "./components/CategoryPills";
import CasesBarChart from "./components/CasesBarChart";
import DecisionPieChart from "./components/DecisionPieChart";
import CasesTable from "./components/CasesTable";
import ThemeToggle from "./components/ThemeToggle";

const API_BASE = "http://localhost:8000";

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [summary, setSummary] = useState(null);
  const [byDay, setByDay] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [investigation, setInvestigation] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [casesRes, summaryRes, byDayRes] = await Promise.all([
        fetch(`${API_BASE}/risk-cases`),
        fetch(`${API_BASE}/risk-dashboard/summary`),
        fetch(`${API_BASE}/risk-dashboard/by-day`),
      ]);

      setCases(await casesRes.json());
      setSummary(await summaryRes.json());
      setByDay(await byDayRes.json());
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    async function loadInvestigation() {
      setInvestigation(null);
      const res = await fetch(`${API_BASE}/investigations/${selectedId}`);
      if (res.ok) setInvestigation(await res.json());
      else {
        const runRes = await fetch(`${API_BASE}/investigations/${selectedId}/run`, { method: "POST" });
        setInvestigation(await runRes.json());
      }
    }
    loadInvestigation();
  }, [selectedId]);

  const filteredCases = useMemo(
    () => (activeFilter === "all" ? cases : cases.filter((c) => c.decision === activeFilter)),
    [cases, activeFilter]
  );

  const pieData = useMemo(() => {
    const counts = { Monitor: 0, Verify: 0, Escalate: 0 };
    cases.forEach((c) => {
      if (c.decision === "MONITOR") counts.Monitor++;
      else if (c.decision === "REQUEST_VERIFICATION") counts.Verify++;
      else if (c.decision === "ESCALATE_TO_HUMAN") counts.Escalate++;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [cases]);

  if (loading) return <div className="empty-state">Loading dashboard…</div>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>Fraud-Spike Investigator</h2>
        <ThemeToggle />
      </div>

      <CategoryPills activeFilter={activeFilter} onFilterChange={setActiveFilter} />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "1.5rem" }}>
        <MetricCard label="Flagged today" value={summary?.total_flagged_cases ?? 0} />
        <MetricCard label="High risk" value={summary?.high_risk_decisions ?? 0} tone="danger" />
        <MetricCard label="Pending review" value={summary?.pending ?? 0} tone="warning" />
        <MetricCard label="Investigated" value={summary?.investigated ?? 0} tone="success" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: "12px", marginBottom: "1.5rem" }}>
        <CasesBarChart data={byDay} />
        <DecisionPieChart data={pieData} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "1.5rem" }}>
        <CasesTable cases={filteredCases} />
        <div style={{ display: "grid", gridTemplateColumns: "180px minmax(0,1fr)", border: "0.5px solid var(--border)", borderRadius: "12px", overflow: "hidden" }}>
          <CaseQueue cases={filteredCases} selectedId={selectedId} onSelect={setSelectedId} />
          <CaseDetail investigation={investigation} onApprove={() => {}} onOverride={() => {}} />
        </div>
      </div>
    </div>
  );
}