import { useState } from "react";
import { CheckCircle, XCircle } from "lucide-react";

interface Props {
  verificationCommand: string;
  onVerify: (payload: {
    verification_status: "VERIFIED" | "VERIFICATION_FAILED";
    evidence_missed?: string;
  }) => Promise<void>;
  submitting: boolean;
  status: "VERIFIED" | "VERIFICATION_FAILED" | "NOT_VERIFIED";
  evidenceMissed?: string;
}

type Mode = "idle" | "failing";

export default function VerificationPanel({
  verificationCommand,
  onVerify,
  submitting,
  status,
  evidenceMissed,
}: Props) {
  const [mode, setMode] = useState<Mode>("idle");
  const [missedReason, setMissedReason] = useState(evidenceMissed || "");

  async function handleVerified() {
    await onVerify({ verification_status: "VERIFIED" });
    setMode("idle");
  }

  async function handleFailed() {
    if (!missedReason.trim()) return;
    await onVerify({
      verification_status: "VERIFICATION_FAILED",
      evidence_missed: missedReason,
    });
    setMode("idle");
  }

  if (status === "VERIFIED") {
    return (
      <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
        <h2 className="text-sm font-semibold text-ink-primary">Verification</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{verificationCommand}</p>
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-signal-pass/30 bg-signal-passDim/40 px-4 py-3 text-sm text-signal-pass">
          <CheckCircle size={16} />
          <span className="font-semibold">Marked as Verified.</span> The fix worked successfully.
        </div>
      </div>
    );
  }

  if (status === "VERIFICATION_FAILED") {
    return (
      <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
        <h2 className="text-sm font-semibold text-ink-primary">Verification</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{verificationCommand}</p>
        <div className="mt-4 flex flex-col gap-2 rounded-lg border border-signal-fail/30 bg-signal-failDim/40 px-4 py-3 text-sm text-signal-fail">
          <div className="flex items-center gap-2 font-semibold">
            <XCircle size={16} /> Verification Failed
          </div>
          <p className="text-xs text-ink-secondary">
            <span className="font-semibold text-ink-primary">Evidence missed:</span> {evidenceMissed}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
      <h2 className="text-sm font-semibold text-ink-primary">Verification</h2>
      <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{verificationCommand}</p>
      
      <div className="mt-4 border-t border-surface-border pt-4">
        <p className="mb-3 text-xs text-ink-secondary">
          Run the command above. Did the fix solve the problem?
        </p>

        {mode === "idle" && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleVerified}
              disabled={submitting}
              className="flex items-center gap-1.5 rounded-md bg-signal-pass px-3.5 py-2 text-sm font-semibold text-[#06231A] transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              <CheckCircle size={15} /> Fix worked (Verified)
            </button>
            <button
              onClick={() => setMode("failing")}
              disabled={submitting}
              className="flex items-center gap-1.5 rounded-md border border-signal-fail/40 bg-signal-failDim/50 px-3.5 py-2 text-sm font-semibold text-signal-fail transition-colors hover:bg-signal-failDim disabled:opacity-50"
            >
              <XCircle size={14} /> Fix failed
            </button>
          </div>
        )}

        {mode === "failing" && (
          <div className="space-y-3 rounded-md border border-signal-fail/25 bg-surface-2/40 p-3">
            <label className="block text-xs font-medium text-ink-secondary">
              What evidence did we miss? <span className="text-signal-fail">(required)</span>
              <textarea
                value={missedReason}
                onChange={(e) => setMissedReason(e.target.value)}
                rows={3}
                placeholder="e.g. The ping still fails because there is an ACL blocking ICMP on the return path."
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-1 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-fail focus:outline-none"
              />
            </label>
            <div className="flex gap-2">
              <button
                onClick={handleFailed}
                disabled={submitting || !missedReason.trim()}
                className="rounded-md bg-signal-fail px-3.5 py-2 text-sm font-semibold text-[#2C0705] hover:opacity-90 disabled:opacity-50"
              >
                Submit Failure
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
