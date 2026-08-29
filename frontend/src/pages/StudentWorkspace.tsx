import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  CheckCircle2,
  Circle,
  Clock,
  Eye,
  GraduationCap,
  ListChecks,
  Loader2,
  Target,
  type LucideIcon,
} from "lucide-react";
import { api, ApiError } from "../services/api";
import type { Case, CaseStatusMap, WorkspaceSummary } from "../services/types";
import { useStudent } from "../context/StudentContext";
import SafetyBanner from "../components/SafetyBanner";
import { CaseProgressBadge, CaseSeverityBadge } from "../components/Badges";

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

export default function StudentWorkspace() {
  const { studentName, setStudentName } = useStudent();
  const [nameInput, setNameInput] = useState(studentName);

  const [summary, setSummary] = useState<WorkspaceSummary | null>(null);
  const [cases, setCases] = useState<Case[] | null>(null);
  const [caseStatus, setCaseStatus] = useState<CaseStatusMap["case_status"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [conceptFilter, setConceptFilter] = useState<string | null>(null);

  function loadWorkspaceData(name: string) {
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    Promise.all([
      api.getWorkspaceSummary(name),
      api.listCases(),
      api.getCaseStatusMap(name),
    ])
      .then(([summaryData, caseData, statusData]) => {
        setSummary(summaryData);
        setCases(caseData);
        setCaseStatus(statusData);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load workspace"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (studentName.trim()) {
      loadWorkspaceData(studentName);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentName]);

  function handleNameSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = nameInput.trim();
    if (trimmed) setStudentName(trimmed);
  }

  async function handleSelectCase(caseId: string) {
    if (!studentName.trim()) return;
    try {
      await api.startAttempt(caseId, studentName);
    } catch {
      // Non-fatal: if attempt tracking fails, the student should still
      // be able to open and work the case - navigation continues below.
    }
  }

  if (!studentName.trim()) {
    return (
      <div className="mx-auto max-w-md space-y-5 py-12">
        <div className="text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-signal-passDim">
            <GraduationCap size={22} className="text-signal-pass" />
          </span>
          <h1 className="mt-3 text-xl font-semibold text-ink-primary">Student Workspace</h1>
          <p className="mt-1.5 text-sm text-ink-secondary">
            Enter a name to track your progress across cases. This isn't a login - just a label
            saved on this device so your attempt history persists between visits.
          </p>
        </div>
        <form onSubmit={handleNameSubmit} className="flex gap-2">
          <input
            autoFocus
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            placeholder="Your name"
            className="flex-1 rounded-md border border-surface-border bg-surface-1 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-info focus:outline-none"
          />
          <button
            type="submit"
            disabled={!nameInput.trim()}
            className="rounded-md bg-signal-pass px-4 py-2 text-sm font-semibold text-[#06231A] transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            Start
          </button>
        </form>
      </div>
    );
  }

  const filteredCases = cases?.filter((c) => !conceptFilter || c.concept === conceptFilter) ?? [];

  return (
    <div className="space-y-6 pb-16">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink-primary">Student Workspace</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            Signed in as <span className="font-medium text-ink-primary">{studentName}</span>
          </p>
        </div>
        <button
          onClick={() => {
            setStudentName("");
            setNameInput("");
          }}
          className="text-xs font-medium text-ink-muted hover:text-ink-secondary hover:underline"
        >
          Not you? Switch name
        </button>
      </div>

      <SafetyBanner />

      {error && (
        <div className="rounded-md border border-signal-fail/30 bg-signal-failDim/40 px-3 py-2.5 text-sm text-signal-fail">
          {error}
        </div>
      )}

      {loading && !summary ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg border border-surface-border bg-surface-1" />
          ))}
        </div>
      ) : summary ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={ListChecks}
              label="Available cases"
              value={summary.total_available_cases}
              accent="bg-signal-infoDim text-signal-info"
            />
            <StatCard
              icon={Clock}
              label="Attempted"
              value={summary.attempted_count}
              accent="bg-signal-warnDim text-signal-warn"
            />
            <StatCard
              icon={CheckCircle2}
              label="Completed"
              value={summary.completed_count}
              accent="bg-signal-passDim text-signal-pass"
            />
            <StatCard
              icon={Circle}
              label="In review / in progress"
              value={summary.in_progress_count}
              accent="bg-surface-2 text-ink-secondary"
            />
          </div>

          <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
            <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-ink-primary">
              <BookOpen size={14} className="text-signal-teal" /> Practice by concept
            </h2>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setConceptFilter(null)}
                className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                  conceptFilter === null
                    ? "border-signal-info/40 bg-signal-infoDim/40 text-signal-info"
                    : "border-surface-border text-ink-secondary hover:bg-surface-2"
                }`}
              >
                All cases
              </button>
              {Object.entries(summary.practice_by_concept)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([concept, progress]) => (
                  <button
                    key={concept}
                    onClick={() => setConceptFilter(concept)}
                    className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                      conceptFilter === concept
                        ? "border-signal-info/40 bg-signal-infoDim/40 text-signal-info"
                        : "border-surface-border text-ink-secondary hover:bg-surface-2"
                    }`}
                  >
                    {concept}
                    <span className="font-mono text-[10px] opacity-70">
                      {progress.completed}/{progress.total}
                    </span>
                  </button>
                ))}
            </div>
          </div>

          <div>
            <h2 className="mb-3 text-sm font-semibold text-ink-primary">
              {conceptFilter ? `${conceptFilter} cases` : "All cases"}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {filteredCases.map((c) => (
                <div
                  key={c.case_id}
                  className="group flex flex-col rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel transition-colors hover:border-signal-info/40 hover:bg-surface-2/60"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[11px] font-semibold text-signal-info">
                      {c.case_id}
                    </span>
                    <CaseProgressBadge status={caseStatus?.[c.case_id] ?? "not_started"} />
                  </div>
                  <Link
                    to={`/practice/${c.case_id}`}
                    onClick={() => handleSelectCase(c.case_id)}
                    className="mt-2 text-sm font-semibold text-ink-primary group-hover:text-white"
                  >
                    {c.title}
                  </Link>
                  <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-ink-secondary">
                    {c.symptom}
                  </p>
                  <div className="mt-3 flex items-center gap-1.5 text-[11px] text-ink-muted">
                    <span className="rounded border border-surface-border px-1.5 py-0.5">
                      {c.osi_layer}
                    </span>
                    <CaseSeverityBadge severity={c.severity} />
                    <span className="ml-auto">{c.difficulty}</span>
                  </div>
                  <div className="mt-3 flex gap-2 border-t border-surface-border pt-3">
                    <Link
                      to={`/practice/${c.case_id}`}
                      onClick={() => handleSelectCase(c.case_id)}
                      className="flex flex-1 items-center justify-center gap-1 rounded-md bg-signal-pass px-2.5 py-1.5 text-xs font-semibold text-[#06231A] transition-opacity hover:opacity-90"
                    >
                      <Target size={12} /> Practice
                    </Link>
                    <Link
                      to={`/cases/${c.case_id}`}
                      onClick={() => handleSelectCase(c.case_id)}
                      className="flex flex-1 items-center justify-center gap-1 rounded-md border border-surface-border px-2.5 py-1.5 text-xs font-medium text-ink-secondary transition-colors hover:bg-surface-2"
                    >
                      <Eye size={12} /> Review
                    </Link>
                  </div>
                </div>
              ))}
              {filteredCases.length === 0 && (
                <p className="col-span-full py-8 text-center text-sm text-ink-muted">
                  No cases in this category yet.
                </p>
              )}
            </div>
          </div>
        </>
      ) : loading ? (
        <div className="flex items-center justify-center py-12 text-ink-muted">
          <Loader2 size={18} className="animate-spin" />
        </div>
      ) : null}
    </div>
  );
}
