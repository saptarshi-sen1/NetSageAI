import { useState } from "react";
import { Check, Pencil, ShieldCheck, X } from "lucide-react";
import type { AIDiagnosis, ReviewDecision } from "../services/types";

interface Props {
  caseId: string;
  diagnosis: AIDiagnosis;
  onSubmit: (payload: {
    human_decision: ReviewDecision;
    human_root_cause: string;
    correction_reason: string;
    reviewer: string;
  }) => Promise<void>;
  submitting: boolean;
  lastDecision: ReviewDecision | null;
}

type Mode = "idle" | "editing" | "rejecting";

export default function ReviewPanel({ diagnosis, onSubmit, submitting, lastDecision }: Props) {
  const [mode, setMode] = useState<Mode>("idle");
  const [reviewer, setReviewer] = useState("");
  const [editedRootCause, setEditedRootCause] = useState(diagnosis.root_cause);
  const [rejectReason, setRejectReason] = useState("");
  const [editReason, setEditReason] = useState("");

  const reviewerOrDefault = () => (reviewer.trim() ? reviewer.trim() : "Anonymous Reviewer");

  async function handleAccept() {
    await onSubmit({
      human_decision: "ACCEPTED",
      human_root_cause: "",
      correction_reason: "",
      reviewer: reviewerOrDefault(),
    });
    setMode("idle");
  }

  async function handleEditSubmit() {
    await onSubmit({
      human_decision: "EDITED",
      human_root_cause: editedRootCause,
      correction_reason: editReason,
      reviewer: reviewerOrDefault(),
    });
    setMode("idle");
  }

  async function handleRejectSubmit() {
    if (!rejectReason.trim()) return;
    await onSubmit({
      human_decision: "REJECTED",
      human_root_cause: "",
      correction_reason: rejectReason,
      reviewer: reviewerOrDefault(),
    });
    setMode("idle");
  }

  if (lastDecision) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-signal-pass/30 bg-signal-passDim/40 px-4 py-3 text-sm text-signal-pass">
        <ShieldCheck size={16} />
        Review recorded as <span className="font-semibold">{lastDecision}</span>. Thank you for
        keeping a human in the loop.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-surface-border bg-surface-1 shadow-panel">
      <div className="border-b border-surface-border px-4 py-3">
        <h3 className="text-sm font-semibold text-ink-primary">Human Review</h3>
        <p className="mt-0.5 text-xs text-ink-muted">
          This diagnosis cannot be applied to any device until you decide below.
        </p>
      </div>

      <div className="space-y-3 px-4 py-4">
        <label className="block text-xs font-medium text-ink-secondary">
          Reviewer name (optional)
          <input
            value={reviewer}
            onChange={(e) => setReviewer(e.target.value)}
            placeholder="Anonymous Reviewer"
            className="mt-1 w-full rounded-md border border-surface-border bg-surface-2 px-3 py-1.5 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-info focus:outline-none"
          />
        </label>

        {mode === "idle" && (
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              onClick={handleAccept}
              disabled={submitting}
              className="flex items-center gap-1.5 rounded-md bg-signal-pass px-3.5 py-2 text-sm font-semibold text-[#06231A] transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              <Check size={15} /> Accept
            </button>
            <button
              onClick={() => setMode("editing")}
              disabled={submitting}
              className="flex items-center gap-1.5 rounded-md border border-signal-info/40 bg-signal-infoDim/50 px-3.5 py-2 text-sm font-semibold text-signal-info transition-colors hover:bg-signal-infoDim disabled:opacity-50"
            >
              <Pencil size={14} /> Edit
            </button>
            <button
              onClick={() => setMode("rejecting")}
              disabled={submitting}
              className="flex items-center gap-1.5 rounded-md border border-signal-fail/40 bg-signal-failDim/50 px-3.5 py-2 text-sm font-semibold text-signal-fail transition-colors hover:bg-signal-failDim disabled:opacity-50"
            >
              <X size={14} /> Reject
            </button>
          </div>
        )}

        {mode === "editing" && (
          <div className="space-y-3 rounded-md border border-signal-info/25 bg-surface-2/40 p-3">
            <label className="block text-xs font-medium text-ink-secondary">
              Corrected root cause
              <textarea
                value={editedRootCause}
                onChange={(e) => setEditedRootCause(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-1 px-3 py-2 text-sm text-ink-primary focus:border-signal-info focus:outline-none"
              />
            </label>
            <label className="block text-xs font-medium text-ink-secondary">
              Why did you edit this? (optional but helps the Responsible AI log)
              <textarea
                value={editReason}
                onChange={(e) => setEditReason(e.target.value)}
                rows={2}
                placeholder="e.g. AI identified the right category but was too vague to act on directly"
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-1 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-info focus:outline-none"
              />
            </label>
            <div className="flex gap-2">
              <button
                onClick={handleEditSubmit}
                disabled={submitting || !editedRootCause.trim()}
                className="rounded-md bg-signal-info px-3.5 py-2 text-sm font-semibold text-[#0A2733] hover:opacity-90 disabled:opacity-50"
              >
                Submit edited diagnosis
              </button>
              <button
                onClick={() => setMode("idle")}
                className="rounded-md border border-surface-border px-3.5 py-2 text-sm text-ink-secondary hover:bg-surface-2"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {mode === "rejecting" && (
          <div className="space-y-3 rounded-md border border-signal-fail/25 bg-surface-2/40 p-3">
            <label className="block text-xs font-medium text-ink-secondary">
              Reason for rejection <span className="text-signal-fail">(required)</span>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={3}
                placeholder="e.g. Evidence contradicts this - the routing table shows the destination network is present, so this isn't a missing-route issue"
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-1 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-fail focus:outline-none"
              />
            </label>
            <div className="flex gap-2">
              <button
                onClick={handleRejectSubmit}
                disabled={submitting || !rejectReason.trim()}
                className="rounded-md bg-signal-fail px-3.5 py-2 text-sm font-semibold text-[#2C0705] hover:opacity-90 disabled:opacity-50"
              >
                Submit rejection
              </button>
              <button
                onClick={() => setMode("idle")}
                className="rounded-md border border-surface-border px-3.5 py-2 text-sm text-ink-secondary hover:bg-surface-2"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
