import { ArrowRight, Sparkles, Wrench, ListChecks, Terminal, Brain, ClipboardCheck } from "lucide-react";
import type { AIDiagnosis, EvidenceHighlight } from "../services/types";
import { ConfidenceBadge } from "./Badges";
import EvidenceHighlightedOutput from "./EvidenceHighlightedOutput";

export default function AIDiagnosisCard({
  diagnosis,
  showOutputs,
  evidenceHighlights,
}: {
  diagnosis: AIDiagnosis;
  showOutputs: string;
  evidenceHighlights: EvidenceHighlight[] | null;
}) {
  return (
    <div className="rounded-lg border border-signal-info/25 bg-surface-1 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-signal-info" />
          <h3 className="text-sm font-semibold text-ink-primary">AI Diagnosis</h3>
          <span className="rounded border border-surface-border px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-ink-muted">
            {diagnosis.osi_layer} · {diagnosis.concept}
          </span>
        </div>
        <ConfidenceBadge label={diagnosis.confidence_label} value={diagnosis.confidence} />
      </div>

      <div className="space-y-5 px-4 py-4">
        {/* Stage 1: Observed Evidence - grounded in the raw show output,
            with byte-exact highlights where a match was actually found. */}
        <section>
          <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-signal-info">
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-signal-infoDim text-[10px]">
              1
            </span>
            Observed evidence
          </p>
          <p className="mt-1 text-[11px] text-ink-muted">
            What the AI says it found in the supplied show-command output. Select an item to
            highlight it below - the raw output stays fully visible so you can verify this
            yourself.
          </p>
          <div className="mt-2">
            <EvidenceHighlightedOutput
              showOutputs={showOutputs}
              evidenceHighlights={evidenceHighlights ?? []}
              fallbackEvidence={diagnosis.evidence}
              defaultOpen
            />
          </div>
        </section>

        {/* Stage 2: AI Interpretation - the root cause + reasoning that
            connects the evidence above to a conclusion. Kept visually
            distinct from the raw evidence so it's clear this is
            interpretation, not another observed fact. */}
        <section>
          <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-signal-teal">
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-signal-info/10 text-[10px]">
              2
            </span>
            AI interpretation
          </p>
          <div className="mt-2 space-y-3 rounded-md border border-surface-border bg-surface-2/40 p-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                Root cause
              </p>
              <p className="mt-1 text-[15px] leading-relaxed text-ink-primary">
                {diagnosis.root_cause}
              </p>
            </div>
            <div>
              <p className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                <Brain size={11} /> Reasoning
              </p>
              <p className="mt-1 text-sm leading-relaxed text-ink-secondary">
                {diagnosis.reasoning_summary}
              </p>
            </div>
          </div>
        </section>

        {/* Stage 3: Recommendation - next command, fix, verification.
            Explicitly advisory, never auto-applied. */}
        <section>
          <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-signal-pass">
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-signal-passDim text-[10px]">
              3
            </span>
            Recommendation
          </p>
          <div className="mt-2 space-y-3">
            {diagnosis.next_command && (
              <div className="flex items-start gap-2 rounded-md border border-surface-border bg-surface-2/60 px-3 py-2">
                <Terminal size={14} className="mt-0.5 shrink-0 text-signal-amber" />
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                    Suggested next command
                  </p>
                  <p className="mt-0.5 font-mono text-[12.5px] text-ink-primary">
                    {diagnosis.next_command}
                  </p>
                </div>
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              {diagnosis.fix_steps.length > 0 && (
                <div>
                  <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                    <Wrench size={12} /> Suggested fix steps
                  </p>
                  <ol className="mt-1.5 space-y-1">
                    {diagnosis.fix_steps.map((step, i) => (
                      <li key={i} className="flex gap-2 text-sm text-ink-secondary">
                        <span className="font-mono text-[11px] text-ink-muted">{i + 1}.</span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {diagnosis.verification_steps.length > 0 && (
                <div>
                  <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                    <ListChecks size={12} /> Verification steps
                  </p>
                  <ol className="mt-1.5 space-y-1">
                    {diagnosis.verification_steps.map((step, i) => (
                      <li key={i} className="flex gap-2 text-sm text-ink-secondary">
                        <ArrowRight size={12} className="mt-1 shrink-0 text-signal-pass" />
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>

            <p className="flex items-center gap-1.5 text-[11px] text-ink-muted">
              <ClipboardCheck size={12} />
              This is a suggestion only - a human reviewer must accept, edit, or reject it below
              before anything is considered resolved.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
