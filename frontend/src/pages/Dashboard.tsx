import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { FileWarning, GaugeCircle, ListChecks, ShieldCheck, type LucideIcon } from "lucide-react";
import { api, ApiError } from "../services/api";
import type { DashboardData } from "../services/types";
import SafetyBanner from "../components/SafetyBanner";
import { DecisionBadge } from "../components/Badges";

const CHART_COLORS = ["#4FB8E8", "#2FD9C4", "#F5B942", "#F1594C", "#8B7CF6", "#6B7789"];

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  accent: string;
}) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
      <div className="flex items-center gap-2">
        <span className={`flex h-7 w-7 items-center justify-center rounded-md ${accent}`}>
          <Icon size={15} />
        </span>
        <span className="text-xs font-medium uppercase tracking-wide text-ink-muted">
          {label}
        </span>
      </div>
      <p className="mt-2 font-mono text-2xl font-semibold text-ink-primary">{value}</p>
    </div>
  );
}

function ChartPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
      <h3 className="mb-3 text-sm font-semibold text-ink-primary">{title}</h3>
      <div className="h-64">{children}</div>
    </div>
  );
}

function objectToChartData(obj: Record<string, number>) {
  return Object.entries(obj)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDashboard()
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load dashboard"));
  }, []);

  if (error) {
    return (
      <div className="rounded-lg border border-signal-fail/30 bg-signal-failDim/40 px-4 py-3 text-sm text-signal-fail">
        Couldn't load the dashboard: {error}. Is the backend running on :8000?
      </div>
    );
  }

  if (!data) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-lg border border-surface-border bg-surface-1" />
        ))}
      </div>
    );
  }

  const decisionData = [
    { name: "Accepted", value: data.decision_counts.ACCEPTED ?? 0 },
    { name: "Edited", value: data.decision_counts.EDITED ?? 0 },
    { name: "Rejected", value: data.decision_counts.REJECTED ?? 0 },
  ];
  const decisionColors: Record<string, string> = {
    Accepted: "#2FD98A",
    Edited: "#4FB8E8",
    Rejected: "#F1594C",
  };

  return (
    <div className="space-y-6 pb-16">
      <div>
        <h1 className="text-xl font-semibold text-ink-primary">NetSage AI</h1>
        <p className="mt-1 text-sm text-ink-secondary">
          AI-assisted network troubleshooting with human review.
        </p>
      </div>

      <SafetyBanner />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={ListChecks}
          label="Total cases"
          value={data.total_cases}
          accent="bg-signal-infoDim text-signal-info"
        />
        <StatCard
          icon={ShieldCheck}
          label="Reviewed"
          value={data.reviewed}
          accent="bg-signal-passDim text-signal-pass"
        />
        <StatCard
          icon={GaugeCircle}
          label="AI agreement"
          value={`${data.agreement_rate_percent}%`}
          accent="bg-signal-warnDim text-signal-warn"
        />
        <StatCard
          icon={FileWarning}
          label="Corrections (edited + rejected)"
          value={(data.decision_counts.EDITED ?? 0) + (data.decision_counts.REJECTED ?? 0)}
          accent="bg-signal-failDim text-signal-fail"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartPanel title="Cases by concept">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={objectToChartData(data.cases_by_concept)} layout="vertical" margin={{ left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-surface-border)" horizontal={false} />
              <XAxis type="number" stroke="var(--color-ink-muted)" fontSize={11} allowDecimals={false} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="var(--color-ink-secondary)"
                fontSize={11}
                width={160}
              />
              <Tooltip
                contentStyle={{ background: "var(--color-surface-2)", border: "1px solid var(--color-surface-border)", borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: "rgba(255,255,255,0.03)" }}
              />
              <Bar dataKey="value" fill="#4FB8E8" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Cases by severity">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={objectToChartData(data.cases_by_severity)}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={2}
              >
                {objectToChartData(data.cases_by_severity).map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "var(--color-surface-2)", border: "1px solid var(--color-surface-border)", borderRadius: 8, fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Cases by OSI layer">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={objectToChartData(data.cases_by_osi_layer)}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-surface-border)" vertical={false} />
              <XAxis dataKey="name" stroke="var(--color-ink-secondary)" fontSize={11} />
              <YAxis stroke="var(--color-ink-muted)" fontSize={11} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: "var(--color-surface-2)", border: "1px solid var(--color-surface-border)", borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: "rgba(128,128,128,0.1)" }}
              />
              <Bar dataKey="value" fill="#2FD9C4" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Accepted vs Edited vs Rejected">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={decisionData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={2}
              >
                {decisionData.map((d, i) => (
                  <Cell key={i} fill={decisionColors[d.name] ?? CHART_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "var(--color-surface-2)", border: "1px solid var(--color-surface-border)", borderRadius: 8, fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="AI vs human agreement">
          <div className="flex h-full flex-col items-center justify-center gap-2">
            <div className="relative flex h-36 w-36 items-center justify-center rounded-full border-8 border-surface-2">
              <div
                className="absolute inset-0 rounded-full"
                style={{
                  background: `conic-gradient(#2FD98A ${data.agreement_rate_percent}%, #212C3D 0)`,
                  mask: "radial-gradient(farthest-side, transparent calc(100% - 10px), black calc(100% - 10px))",
                  WebkitMask: "radial-gradient(farthest-side, transparent calc(100% - 10px), black calc(100% - 10px))",
                }}
              />
              <span className="font-mono text-2xl font-semibold text-ink-primary">
                {data.agreement_rate_percent}%
              </span>
            </div>
            <p className="text-center text-xs text-ink-muted">
              of reviewed diagnoses were accepted as-is · avg. AI confidence{" "}
              {Math.round(data.average_ai_confidence * 100)}%
            </p>
          </div>
        </ChartPanel>

        <ChartPanel title="Rule-checker findings (by rule)">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={objectToChartData(data.rule_hit_counts).slice(0, 8)}
              layout="vertical"
              margin={{ left: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-surface-border)" horizontal={false} />
              <XAxis type="number" stroke="var(--color-ink-muted)" fontSize={11} allowDecimals={false} />
              <YAxis type="category" dataKey="name" stroke="var(--color-ink-secondary)" fontSize={11} width={160} />
              <Tooltip
                contentStyle={{ background: "var(--color-surface-2)", border: "1px solid var(--color-surface-border)", borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: "rgba(255,255,255,0.03)" }}
              />
              <Bar dataKey="value" fill="#F5B942" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Corrections by concept (Edited + Rejected)">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={objectToChartData(data.corrections_by_concept)}
              layout="vertical"
              margin={{ left: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-surface-border)" horizontal={false} />
              <XAxis type="number" stroke="var(--color-ink-muted)" fontSize={11} allowDecimals={false} />
              <YAxis type="category" dataKey="name" stroke="var(--color-ink-secondary)" fontSize={11} width={160} />
              <Tooltip
                contentStyle={{ background: "var(--color-surface-2)", border: "1px solid var(--color-surface-border)", borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: "rgba(128,128,128,0.1)" }}
              />
              <Bar dataKey="value" fill="#F1594C" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Corrections by severity">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={objectToChartData(data.corrections_by_severity)}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={2}
              >
                {objectToChartData(data.corrections_by_severity).map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[(i + 2) % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "var(--color-surface-2)", border: "1px solid var(--color-surface-border)", borderRadius: 8, fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>

      <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold text-ink-primary">Recent reviews</h3>
        {data.recent_reviews.length === 0 ? (
          <p className="text-sm text-ink-muted">No reviews recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {data.recent_reviews.map((r) => (
              <Link
                key={r.review_id}
                to={`/cases/${r.case_id}`}
                className="flex flex-col gap-1.5 rounded-md border border-surface-border bg-surface-2/40 px-3 py-2.5 transition-colors hover:bg-surface-2 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] text-signal-info">{r.case_id}</span>
                  <DecisionBadge decision={r.human_decision} />
                </div>
                <span className="line-clamp-1 text-xs text-ink-secondary sm:max-w-md">
                  {r.human_root_cause || r.ai_root_cause}
                </span>
                <span className="text-[11px] text-ink-muted">{r.reviewer}</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold text-ink-primary">Student Lab Performance</h3>
        {(!data.student_progress || data.student_progress.length === 0) ? (
          <p className="text-sm text-ink-muted">No student attempts recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border text-ink-muted">
                  <th className="pb-2 font-medium">Case ID</th>
                  <th className="pb-2 font-medium text-right">Total Attempts</th>
                  <th className="pb-2 font-medium text-right">Completed</th>
                  <th className="pb-2 font-medium text-right">Success Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/50">
                {data.student_progress.map((stat) => (
                  <tr key={stat.case_id} className="text-ink-secondary">
                    <td className="py-2.5">
                      <Link to={`/cases/${stat.case_id}`} className="font-mono text-[11px] text-signal-info hover:underline">
                        {stat.case_id}
                      </Link>
                    </td>
                    <td className="py-2.5 text-right">{stat.total_attempts}</td>
                    <td className="py-2.5 text-right">{stat.completed}</td>
                    <td className="py-2.5 text-right">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        stat.success_rate_percent >= 80 ? 'bg-signal-passDim/40 text-signal-pass' :
                        stat.success_rate_percent >= 50 ? 'bg-signal-warnDim/40 text-signal-warn' :
                        'bg-signal-failDim/40 text-signal-fail'
                      }`}>
                        {stat.success_rate_percent}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
