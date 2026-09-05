import { useState, useEffect, useMemo } from "react";
import MetricCard from "./components/MetricCard";
import CaseQueue from "./components/CaseQueue";
import CaseDetail from "./components/CaseDetail";
import CategoryPills from "./components/CategoryPills";
import CasesBarChart from "./components/CasesBarChart";
import DecisionPieChart from "./components/DecisionPieChart";
import CasesTable from "./components/CasesTable";
import ThemeToggle from "./components/ThemeToggle";
import CostCurveSlider from "./components/CostCurveSlider";

const API_BASE = "http://localhost:8000";

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [summary, setSummary] = useState(null);
  const [byDayData, setByDayData] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [investigation, setInvestigation] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  // Load cases and dashboard summary
  useEffect(() => {
    async function loadData() {
      try {
        const [casesRes, summaryRes] = await Promise.all([
          fetch(`${API_BASE}/risk-cases`),
          fetch(`${API_BASE}/risk-dashboard/summary`),
        ]);

        setCases(await casesRes.json());
        setSummary(await summaryRes.json());
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  // Fetch cases-by-day data for the bar chart
  useEffect(() => {
    fetch(`${API_BASE}/risk-dashboard/by-day`)
      .then((r) => r.json())
      .then(setByDayData)
      .catch(console.error);
  }, []);

  // Load existing investigation or run a new one
  useEffect(() => {
    if (!selectedId) return;

    async function loadInvestigation() {
      try {
        setInvestigation(null);

        const res = await fetch(
          `${API_BASE}/investigations/${selectedId}`
        );

        if (res.ok) {
          setInvestigation(await res.json());
        } else {
          const runRes = await fetch(
            `${API_BASE}/investigations/${selectedId}/run`,
            { method: "POST" }
          );

          if (!runRes.ok) {
            throw new Error("Failed to run investigation");
          }

          setInvestigation(await runRes.json());
        }
      } catch (err) {
        console.error(err);
      }
    }

    loadInvestigation();
  }, [selectedId]);

  // Approve the AI-generated decision
  async function handleApprove() {
    if (!selectedId || !investigation) return;

    try {
      const res = await fetch(
        `${API_BASE}/investigations/${selectedId}/override`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            human_decision: investigation.decision,
          }),
        }
      );

      if (!res.ok) {
        throw new Error("Failed to approve decision");
      }

      alert("Decision approved and logged.");
    } catch (err) {
      console.error(err);
      alert("Failed to approve decision.");
    }
  }

  // Override the AI-generated decision
  async function handleOverride() {
    if (!selectedId || !investigation) return;

    const decision = prompt(
      "Override decision (ALLOW / MONITOR / REQUEST_VERIFICATION / ESCALATE_TO_HUMAN):"
    );

    if (!decision) return;

    const normalizedDecision = decision.trim().toUpperCase();

    const allowedDecisions = [
      "ALLOW",
      "MONITOR",
      "REQUEST_VERIFICATION",
      "ESCALATE_TO_HUMAN",
    ];

    if (!allowedDecisions.includes(normalizedDecision)) {
      alert(
        "Invalid decision. Please use ALLOW, MONITOR, REQUEST_VERIFICATION, or ESCALATE_TO_HUMAN."
      );
      return;
    }

    try {
      const res = await fetch(
        `${API_BASE}/investigations/${selectedId}/override`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            human_decision: normalizedDecision,
          }),
        }
      );

      if (!res.ok) {
        throw new Error("Failed to override decision");
      }

      alert("Decision overridden.");
    } catch (err) {
      console.error(err);
      alert("Failed to override decision.");
    }
  }

  const filteredCases = useMemo(
    () =>
      activeFilter === "all"
        ? cases
        : cases.filter((c) => c.decision === activeFilter),
    [cases, activeFilter]
  );

  const pieData = useMemo(() => {
    const counts = {
      Monitor: 0,
      Verify: 0,
      Escalate: 0,
    };

    cases.forEach((c) => {
      if (c.decision === "MONITOR") {
        counts.Monitor++;
      } else if (c.decision === "REQUEST_VERIFICATION") {
        counts.Verify++;
      } else if (c.decision === "ESCALATE_TO_HUMAN") {
        counts.Escalate++;
      }
    });

    return Object.entries(counts).map(([name, value]) => ({
      name,
      value,
    }));
  }, [cases]);

  if (loading) {
    return <div className="empty-state">Loading dashboard…</div>;
  }

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h2 style={{ margin: 0 }}>Fraud-Spike Investigator</h2>
        <ThemeToggle />
      </div>

      {/* Decision filters */}
      <CategoryPills
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
      />

      {/* Metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "12px",
          marginBottom: "1.5rem",
        }}
      >
        <MetricCard
          label="Flagged today"
          value={summary?.total_flagged_cases ?? 0}
        />

        <MetricCard
          label="High risk"
          value={summary?.high_risk_decisions ?? 0}
          tone="danger"
        />

        <MetricCard
          label="Pending review"
          value={summary?.pending ?? 0}
          tone="warning"
        />

        <MetricCard
          label="Investigated"
          value={summary?.investigated ?? 0}
          tone="success"
        />
      </div>

      {/* Charts */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.4fr 1fr",
          gap: "12px",
          marginBottom: "1.5rem",
        }}
      >
        <CasesBarChart data={byDayData} />
        <DecisionPieChart data={pieData} />
      </div>

      {/* Cost curve */}
      <div style={{ marginBottom: "1.5rem" }}>
        <CostCurveSlider />
      </div>

      {/* Cases + Queue + Detail */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "12px",
          marginBottom: "1.5rem",
        }}
      >
        <CasesTable cases={filteredCases} />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "180px minmax(0, 1fr)",
            border: "0.5px solid var(--border)",
            borderRadius: "12px",
            overflow: "hidden",
          }}
        >
          <CaseQueue
            cases={filteredCases}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />

          <CaseDetail
            investigation={investigation}
            onApprove={handleApprove}
            onOverride={handleOverride}
          />
        </div>
      </div>
    </div>
  );
}