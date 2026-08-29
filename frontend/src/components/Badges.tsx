import type {
  CaseProgressStatus,
  CaseSource,
  FindingSeverity,
  FindingStatus,
  ReviewDecision,
} from "../services/types";

const STATUS_STYLES: Record<FindingStatus, string> = {
  PASS: "bg-signal-passDim text-signal-pass border-signal-pass/30",
  FAIL: "bg-signal-failDim text-signal-fail border-signal-fail/30",
  WARN: "bg-signal-warnDim text-signal-warn border-signal-warn/30",
};

export function StatusBadge({ status }: { status: FindingStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[11px] font-semibold tracking-wide ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

const SEVERITY_STYLES: Record<FindingSeverity, string> = {
  LOW: "text-ink-muted border-surface-border",
  MEDIUM: "text-signal-warn border-signal-warn/30",
  HIGH: "text-signal-fail border-signal-fail/30",
  CRITICAL: "text-signal-fail border-signal-fail/50 bg-signal-failDim/50",
};

export function SeverityBadge({ severity }: { severity: FindingSeverity | string }) {
  const style = SEVERITY_STYLES[severity as FindingSeverity] ?? SEVERITY_STYLES.LOW;
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium ${style}`}>
      {severity}
    </span>
  );
}

const CASE_SEVERITY_STYLES: Record<string, string> = {
  Low: "text-ink-muted border-surface-border",
  Medium: "text-signal-warn border-signal-warn/30",
  High: "text-signal-fail border-signal-fail/30",
  Critical: "text-signal-fail border-signal-fail/50 bg-signal-failDim/50",
};

export function CaseSeverityBadge({ severity }: { severity: string }) {
  const style = CASE_SEVERITY_STYLES[severity] ?? CASE_SEVERITY_STYLES.Low;
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium ${style}`}>
      {severity}
    </span>
  );
}

const DECISION_STYLES: Record<ReviewDecision, string> = {
  ACCEPTED: "bg-signal-passDim text-signal-pass border-signal-pass/30",
  EDITED: "bg-signal-infoDim text-signal-info border-signal-info/30",
  REJECTED: "bg-signal-failDim text-signal-fail border-signal-fail/30",
};

export function DecisionBadge({ decision }: { decision: ReviewDecision }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-semibold tracking-wide ${DECISION_STYLES[decision]}`}
    >
      {decision}
    </span>
  );
}

export function ConfidenceBadge({
  label,
  value,
}: {
  label: "Low" | "Medium" | "High";
  value: number;
}) {
  const styles: Record<string, string> = {
    Low: "bg-signal-failDim text-signal-fail border-signal-fail/30",
    Medium: "bg-signal-warnDim text-signal-warn border-signal-warn/30",
    High: "bg-signal-passDim text-signal-pass border-signal-pass/30",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-semibold ${styles[label]}`}
    >
      {label} confidence
      <span className="font-mono font-normal opacity-80">{Math.round(value * 100)}%</span>
    </span>
  );
}

export function CaseSourceBadge({ source }: { source: CaseSource }) {
  if (source === "seed") {
    return (
      <span className="inline-flex items-center rounded border border-surface-border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ink-muted">
        Course dataset
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded border border-signal-teal/30 bg-signal-info/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-signal-teal">
      User-created
    </span>
  );
}

export function ArchivedBadge() {
  return (
    <span className="inline-flex items-center rounded border border-ink-muted/30 bg-surface-2 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ink-muted">
      Archived
    </span>
  );
}

const PROGRESS_STYLES: Record<CaseProgressStatus, string> = {
  not_started: "border-surface-border text-ink-muted",
  in_progress: "bg-signal-warnDim text-signal-warn border-signal-warn/30",
  completed: "bg-signal-passDim text-signal-pass border-signal-pass/30",
};

const PROGRESS_LABELS: Record<CaseProgressStatus, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  completed: "Completed",
};

export function CaseProgressBadge({ status }: { status: CaseProgressStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${PROGRESS_STYLES[status]}`}
    >
      {PROGRESS_LABELS[status]}
    </span>
  );
}
