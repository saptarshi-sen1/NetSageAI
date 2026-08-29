import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  GraduationCap,
  Loader2,
  RotateCcw,
  Sparkles,
  Target,
  XCircle,
} from "lucide-react";
import { api, ApiError } from "../services/api";
import type { PracticeCaseView, PracticeComparisonResult } from "../services/types";
import { useStudent } from "../context/StudentContext";
import SafetyBanner from "../components/SafetyBanner";
import ShowOutputBlock from "../components/ShowOutputBlock";
import EvidenceHighlightedOutput from "../components/EvidenceHighlightedOutput";
import { ConfidenceBadge } from "../components/Badges";

const OSI_LAYERS = ["Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 7"];

export default function PracticeMode() {
  const { caseId } = useParams<{ caseId: string }>();
  const { studentName } = useStudent();

  const [practiceCase, setPracticeCase] = useState<PracticeCaseView | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [rootCause, setRootCause] = useState("");
  const [osiLayer, setOsiLayer] = useState("");
  const [nextCommand, setNextCommand] = useState("");
  const [fix, setFix] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<PracticeComparisonResult | null>(null);

  useEffect(() => {
    if (!caseId) return;
    setPracticeCase(null);
    setResult(null);
    setRootCause("");
    setOsiLayer("");
    setNextCommand("");
    setFix("");
    api
      .getPracticeCase(caseId)
      .then(setPracticeCase)
      .catch((e) => setLoadError(e instanceof ApiError ? e.message : "Failed to load case"));
  }, [caseId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!caseId || !rootCause.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const comparison = await api.submitPractice({
        case_id: caseId,
        student_name: studentName || "Anonymous",
        student_root_cause: rootCause,
        student_osi_layer: osiLayer,
        student_next_command: nextCommand,
        student_fix: fix,
      });
      setResult(comparison);
    } catch (e) {
      setSubmitError(e instanceof ApiError ? e.message : "Failed to submit your answer");
    } finally {
      setSubmitting(false);
    }
  }

  function handleTryAgain() {
    setResult(null);
    setRootCause("");
    setOsiLayer("");
    setNextCommand("");
    setFix("");
  }

  if (loadError) {
    return (
      <div className="space-y-4">
        <Link to="/workspace" className="flex items-center gap-1 text-sm text-ink-secondary hover:text-ink-primary">
          <ArrowLeft size={14} /> Back to workspace
        </Link>
        <div className="rounded-lg border border-signal-fail/30 bg-signal-failDim/40 px-4 py-3 text-sm text-signal-fail">
          {loadError}
        </div>
      </div>
    );
  }

  if (!practiceCase) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-40 animate-pulse rounded bg-surface-1" />
        <div className="h-40 animate-pulse rounded-lg border border-surface-border bg-surface-1" />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-16">
      <div className="flex items-center justify-between">
        <Link to="/workspace" className="flex items-center gap-1 text-sm text-ink-secondary hover:text-ink-primary">
          <ArrowLeft size={14} /> Back to workspace
        </Link>
        <span className="font-mono text-xs text-ink-muted">{practiceCase.case_id}</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-signal-passDim">
          <GraduationCap size={16} className="text-signal-pass" />
        </span>
        <h1 className="text-xl font-semibold text-ink-primary">{practiceCase.title}</h1>
        <span className="rounded border border-surface-border px-1.5 py-0.5 text-[11px] text-ink-muted">
          {practiceCase.osi_layer}
        </span>
        <span className="rounded border border-surface-border px-1.5 py-0.5 text-[11px] text-ink-muted">
          {practiceCase.concept}
        </span>
      </div>

      <SafetyBanner compact />

      {!result && (
        <p className="rounded-md border border-signal-info/25 bg-signal-infoDim/30 px-3 py-2 text-xs text-signal-info">
          This is Practice Mode: the expected diagnosis is hidden until you submit your own
          answer below. Work through the evidence first.
        </p>
      )}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
          <h2 className="text-sm font-semibold text-ink-primary">Symptom</h2>
          <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{practiceCase.symptom}</p>
        </div>
        <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
          <h2 className="text-sm font-semibold text-ink-primary">Topology note</h2>
          <p className="mt-2 text-sm leading-relaxed text-ink-secondary">
            {practiceCase.topology_note}
          </p>
        </div>
      </section>

      <ShowOutputBlock content={practiceCase.show_outputs} defaultOpen />

      {!result ? (
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel"
        >
          <div className="flex items-center gap-1.5">
            <Target size={15} className="text-signal-pass" />
            <h2 className="text-sm font-semibold text-ink-primary">Your diagnosis</h2>
          </div>
          <p className="text-xs text-ink-muted">
            Submit your best hypothesis based on the evidence above. Once submitted, you'll see
            the AI's independent diagnosis and the expected answer side by side with yours.
          </p>

          {submitError && (
            <div className="rounded-md border border-signal-fail/30 bg-signal-failDim/40 px-3 py-2.5 text-sm text-signal-fail">
              {submitError}
            </div>
          )}

          <label className="block text-xs font-medium text-ink-secondary">
            Suspected root cause <span className="text-signal-fail">*</span>
            <textarea
              value={rootCause}
              onChange={(e) => setRootCause(e.target.value)}
              rows={3}
              required
              placeholder="What do you think is causing this issue, and why?"
              className="mt-1 w-full rounded-md border border-surface-border bg-surface-2 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-info focus:outline-none"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-xs font-medium text-ink-secondary">
              OSI layer
              <select
                value={osiLayer}
                onChange={(e) => setOsiLayer(e.target.value)}
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-2 px-2.5 py-1.5 text-sm text-ink-primary focus:border-signal-info focus:outline-none"
              >
                <option value="">Not sure / skip</option>
                {OSI_LAYERS.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-medium text-ink-secondary">
              Next command you'd run
              <input
                value={nextCommand}
                onChange={(e) => setNextCommand(e.target.value)}
                placeholder="e.g. show vlan brief"
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-2 px-3 py-1.5 font-mono text-[12.5px] text-ink-primary placeholder:font-sans placeholder:text-ink-muted focus:border-signal-info focus:outline-none"
              />
            </label>
          </div>

          <label className="block text-xs font-medium text-ink-secondary">
            Proposed fix
            <textarea
              value={fix}
              onChange={(e) => setFix(e.target.value)}
              rows={2}
              placeholder="What would you change to resolve this?"
              className="mt-1 w-full rounded-md border border-surface-border bg-surface-2 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-info focus:outline-none"
            />
          </label>

          <button
            type="submit"
            disabled={submitting || !rootCause.trim()}
            className="flex items-center gap-1.5 rounded-md bg-signal-pass px-4 py-2 text-sm font-semibold text-[#06231A] transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {submitting && <Loader2 size={14} className="animate-spin" />}
            Submit my diagnosis
          </button>
        </form>
      ) : (
        <ComparisonPanel
          result={result}
          showOutputs={practiceCase.show_outputs}
          onTryAgain={handleTryAgain}
        />
      )}
    </div>
  );
}

function MatchIndicator({ matches }: { matches: boolean }) {
  return matches ? (
    <span className="flex items-center gap-1 text-[11px] font-medium text-signal-pass">
      <CheckCircle2 size={12} /> Heuristic match
    </span>
  ) : (
    <span className="flex items-center gap-1 text-[11px] font-medium text-ink-muted">
      <Circle size={12} /> No automatic match
    </span>
  );
}

function ComparisonPanel({
  result,
  showOutputs,
  onTryAgain,
}: {
  result: PracticeComparisonResult;
  showOutputs: string;
  onTryAgain: () => void;
}) {
  return (
    <div className="space-y-5">
      <SafetyBanner />

      <div className="rounded-md border border-signal-warn/25 bg-signal-warnDim/25 px-3 py-2.5 text-xs leading-relaxed text-signal-warn">
        <strong>How to read the match indicators below:</strong> "Heuristic match" is a loose,
        automated text comparison - it only checks whether your wording and the expected answer
        substantially overlap as text. Free-form answers are often correct even when phrased
        completely differently, and this heuristic can be wrong in both directions. Use it as a
        rough signal, not a grade - read the actual text of all three answers yourself.
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Student */}
        <div className="rounded-lg border border-surface-border bg-surface-1 shadow-panel">
          <div className="flex items-center justify-between border-b border-surface-border px-4 py-3">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink-primary">
              <Target size={14} className="text-signal-pass" /> Your diagnosis
            </h3>
            <MatchIndicator matches={result.student_matches_expected_concept} />
          </div>
          <div className="space-y-3 px-4 py-3 text-sm">
            <Field label="Root cause" value={result.student_root_cause} />
            {result.student_osi_layer && <Field label="OSI layer" value={result.student_osi_layer} />}
            {result.student_next_command && (
              <Field label="Next command" value={result.student_next_command} mono />
            )}
            {result.student_fix && <Field label="Proposed fix" value={result.student_fix} />}
          </div>
        </div>

        {/* AI */}
        <div className="rounded-lg border border-signal-info/25 bg-surface-1 shadow-panel">
          <div className="flex items-center justify-between border-b border-surface-border px-4 py-3">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink-primary">
              <Sparkles size={14} className="text-signal-info" /> AI diagnosis
            </h3>
            {result.ai_confidence_label && (
              <ConfidenceBadge label={result.ai_confidence_label} value={0} />
            )}
          </div>
          <div className="space-y-3 px-4 py-3 text-sm">
            {result.mock_mode && (
              <p className="rounded border border-signal-warn/25 bg-signal-warnDim/30 px-2 py-1 text-[11px] text-signal-warn">
                Demo/mock mode - no live model call was made.
              </p>
            )}
            {result.ai_error ? (
              <p className="text-signal-fail">{result.ai_error}</p>
            ) : (
              <>
                <Field label="Root cause" value={result.ai_root_cause ?? ""} />
                {result.ai_osi_layer && <Field label="OSI layer" value={result.ai_osi_layer} />}
                {result.ai_evidence.length > 0 && (
                  <EvidenceHighlightedOutput
                    showOutputs={showOutputs}
                    evidenceHighlights={result.ai_evidence_highlights}
                    fallbackEvidence={result.ai_evidence}
                  />
                )}
                <MatchIndicator matches={result.ai_matches_expected_concept} />
              </>
            )}
          </div>
        </div>

        {/* Expected */}
        <div className="rounded-lg border border-signal-pass/25 bg-surface-1 shadow-panel">
          <div className="border-b border-surface-border px-4 py-3">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink-primary">
              <CheckCircle2 size={14} className="text-signal-pass" /> Expected diagnosis
            </h3>
          </div>
          <div className="space-y-3 px-4 py-3 text-sm">
            <Field label="Root cause" value={result.expected_fault} />
            <Field label="OSI layer" value={result.expected_osi_layer} />
            {result.expected_evidence && <Field label="Key evidence" value={result.expected_evidence} />}
            {result.expected_next_command && (
              <Field label="Suggested next command" value={result.expected_next_command} mono />
            )}
            {result.expected_fix && <Field label="Suggested fix" value={result.expected_fix} />}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
        <h3 className="text-sm font-semibold text-ink-primary">Learning feedback</h3>
        <ul className="mt-2 space-y-1.5 text-sm text-ink-secondary">
          <li className="flex items-start gap-2">
            {result.student_matches_expected_concept ? (
              <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-signal-pass" />
            ) : (
              <XCircle size={14} className="mt-0.5 shrink-0 text-signal-warn" />
            )}
            <span>
              {result.student_matches_expected_concept
                ? "Your root cause substantially overlaps with the expected answer's wording - a good sign, but read the full expected text above to confirm you identified the same underlying fault, not just similar-sounding words."
                : "Your root cause didn't textually overlap with the expected answer. That doesn't necessarily mean you were wrong - compare the actual reasoning in both, not just this automated flag."}
            </span>
          </li>
          {result.rule_findings_count === 0 && (
            <li className="flex items-start gap-2">
              <Circle size={14} className="mt-0.5 shrink-0 text-ink-muted" />
              <span>
                The deterministic rule checker found no automatic findings for this case - the
                fault required reading the evidence directly rather than pattern-matching, same
                as the AI diagnosis had to.
              </span>
            </li>
          )}
        </ul>
      </div>

      <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
        <h3 className="text-sm font-semibold text-ink-primary">Verification</h3>
        <p className="mt-2 font-mono text-[12.5px] text-ink-secondary">
          {result.verification_command}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={onTryAgain}
          className="flex items-center gap-1.5 rounded-md border border-surface-border px-3.5 py-2 text-sm font-medium text-ink-secondary transition-colors hover:bg-surface-2"
        >
          <RotateCcw size={14} /> Practice this case again
        </button>
        <Link
          to="/workspace"
          className="flex items-center gap-1.5 rounded-md bg-signal-pass px-3.5 py-2 text-sm font-semibold text-[#06231A] transition-opacity hover:opacity-90"
        >
          Back to workspace
        </Link>
      </div>
    </div>
  );
}

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
      <p className={`mt-0.5 leading-relaxed text-ink-primary ${mono ? "font-mono text-[12px]" : ""}`}>
        {value || <span className="text-ink-muted">(not provided)</span>}
      </p>
    </div>
  );
}
