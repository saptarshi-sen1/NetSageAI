import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ListChecks,
  Loader2,
  Network,
  PlayCircle,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import { api, ApiError } from "../services/api";
import type { AIDiagnosis, Case, EvidenceHighlight, Finding, ReviewDecision, Review } from "../services/types";
import ShowOutputBlock from "../components/ShowOutputBlock";
import RuleFindingsList from "../components/RuleFindingsList";
import AIDiagnosisCard from "../components/AIDiagnosisCard";
import ReviewPanel from "../components/ReviewPanel";
import VerificationPanel from "../components/VerificationPanel";
import SafetyBanner from "../components/SafetyBanner";
import PipelineRail, { type PipelineStage } from "../components/PipelineRail";
import { CaseSeverityBadge } from "../components/Badges";

export default function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [checking, setChecking] = useState(false);
  const [diagnosing, setDiagnosing] = useState(false);

  const [diagnosis, setDiagnosis] = useState<AIDiagnosis | null>(null);
  const [evidenceHighlights, setEvidenceHighlights] = useState<EvidenceHighlight[] | null>(null);
  const [mockMode, setMockMode] = useState(false);
  const [modelUsed, setModelUsed] = useState<string | null>(null);
  const [fallbackOccurred, setFallbackOccurred] = useState(false);
  const [isCached, setIsCached] = useState(false);
  const [diagnoseError, setDiagnoseError] = useState<string | null>(null);
  const [submittingReview, setSubmittingReview] = useState(false);
  const [lastDecision, setLastDecision] = useState<ReviewDecision | null>(null);
  const [currentReview, setCurrentReview] = useState<Review | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;
    setCaseData(null);
    setFindings(null);
    setEvidenceHighlights(null);
    setDiagnoseError(null);
    setLastDecision(null);
    setCurrentReview(null);
    setVerifyError(null);
    api
      .getCase(caseId)
      .then(setCaseData)
      .catch((e) => setLoadError(e instanceof ApiError ? e.message : "Failed to load case"));
  }, [caseId]);

  async function handleRunCheck() {
    if (!caseId) return;
    setChecking(true);
    try {
      const res = await api.runCheck(caseId);
      setFindings(res.findings);
    } catch (e) {
      setLoadError(e instanceof ApiError ? e.message : "Check failed");
    } finally {
      setChecking(false);
    }
  }

  async function handleRunDiagnose(force: boolean = false) {
    if (!caseId) return;
    setDiagnosing(true);
    setDiagnoseError(null);
    try {
      const res = await api.runDiagnose(caseId, force);
      if (findings === null) setFindings(res.rule_findings);
      setMockMode(res.mock_mode);
      setModelUsed(res.model_used);
      setFallbackOccurred(res.fallback_occurred);
      setIsCached(res.cached);
      if (res.error) {
        setDiagnoseError(res.error);
        setDiagnosis(null);
        setEvidenceHighlights(null);
      } else {
        setDiagnosis(res.ai_diagnosis);
        setEvidenceHighlights(res.evidence_highlights);
      }
    } catch (e) {
      setDiagnoseError(e instanceof ApiError ? e.message : "Diagnosis request failed");
    } finally {
      setDiagnosing(false);
    }
  }

  async function handleReviewSubmit(payload: {
    human_decision: ReviewDecision;
    human_root_cause: string;
    correction_reason: string;
    reviewer: string;
  }) {
    if (!caseId || !diagnosis) return;
    setSubmittingReview(true);
    setReviewError(null);
    try {
      const review = await api.submitReview({
        case_id: caseId,
        ai_root_cause: diagnosis.root_cause,
        ai_confidence: diagnosis.confidence,
        ...payload,
      });
      setCurrentReview(review);
      setLastDecision(payload.human_decision);
    } catch (e) {
      setReviewError(e instanceof ApiError ? e.message : "Failed to submit review");
    } finally {
      setSubmittingReview(false);
    }
  }

  async function handleVerifySubmit(payload: {
    verification_status: "VERIFIED" | "VERIFICATION_FAILED";
    evidence_missed?: string;
  }) {
    if (!currentReview) return;
    setVerifying(true);
    setVerifyError(null);
    try {
      const updated = await api.verifyReview(currentReview.review_id, payload);
      setCurrentReview(updated);
    } catch (e) {
      setVerifyError(e instanceof ApiError ? e.message : "Failed to verify");
    } finally {
      setVerifying(false);
    }
  }

  const stage: PipelineStage = useMemo(() => {
    if (lastDecision) return "verify";
    if (diagnosis) return "review";
    if (findings !== null) return "ai";
    return "evidence";
  }, [findings, diagnosis, lastDecision]);

  if (loadError) {
    return (
      <div className="space-y-4">
        <Link to="/cases" className="flex items-center gap-1 text-sm text-ink-secondary hover:text-ink-primary">
          <ArrowLeft size={14} /> Back to cases
        </Link>
        <div className="rounded-lg border border-signal-fail/30 bg-signal-failDim/40 px-4 py-3 text-sm text-signal-fail">
          {loadError}
        </div>
      </div>
    );
  }

  if (!caseData) {
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
        <Link to="/cases" className="flex items-center gap-1 text-sm text-ink-secondary hover:text-ink-primary">
          <ArrowLeft size={14} /> Back to cases
        </Link>
        <span className="font-mono text-xs text-ink-muted">{caseData.case_id}</span>
      </div>

      <div className="rounded-lg border border-surface-border bg-surface-1 px-4 py-3 shadow-panel">
        <PipelineRail current={stage} />
      </div>

      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold text-ink-primary">{caseData.title}</h1>
          <CaseSeverityBadge severity={caseData.severity} />
          <span className="rounded border border-surface-border px-1.5 py-0.5 text-[11px] text-ink-muted">
            {caseData.osi_layer}
          </span>
          <span className="rounded border border-surface-border px-1.5 py-0.5 text-[11px] text-ink-muted">
            {caseData.concept}
          </span>
        </div>
      </div>

      <SafetyBanner />

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-ink-primary">
            <AlertTriangle size={14} className="text-signal-warn" /> Symptom
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{caseData.symptom}</p>
        </div>
        <div className="rounded-lg border border-surface-border bg-surface-1 p-4 shadow-panel">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-ink-primary">
            <Network size={14} className="text-signal-info" /> Topology note
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-ink-secondary">
            {caseData.topology_note}
          </p>
        </div>
      </section>

      <ShowOutputBlock content={caseData.show_outputs} />

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-ink-primary">
            <ListChecks size={15} className="text-signal-pass" /> Deterministic rule checker
          </h2>
          <button
            onClick={handleRunCheck}
            disabled={checking}
            className="flex items-center gap-1.5 rounded-md border border-surface-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink-primary transition-colors hover:bg-surface-3 disabled:opacity-50"
          >
            {checking ? <Loader2 size={13} className="animate-spin" /> : <PlayCircle size={13} />}
            {findings === null ? "Run checks" : "Re-run checks"}
          </button>
        </div>
        <p className="text-xs text-ink-muted">
          Same input always produces the same output - no LLM is involved in this step.
        </p>
        {findings !== null && <RuleFindingsList findings={findings} />}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-ink-primary">
            <Sparkles size={15} className="text-signal-info" /> AI diagnosis
          </h2>
          <button
            onClick={() => handleRunDiagnose(!!diagnosis)}
            disabled={diagnosing}
            className="flex items-center gap-1.5 rounded-md bg-signal-info px-3.5 py-1.5 text-xs font-semibold text-[#0A2733] transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {diagnosing ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
            {diagnosis ? "Re-run diagnosis" : "Request AI diagnosis"}
          </button>
        </div>

        {mockMode && (
          <p className="rounded-md border border-signal-warn/25 bg-signal-warnDim/30 px-3 py-1.5 text-xs text-signal-warn">
            Running in demo/mock mode - no AI provider API key is configured, so this response
            comes from a deterministic offline generator, not a live model call.
          </p>
        )}

        {isCached && !mockMode && (
          <p className="rounded-md border border-signal-pass/25 bg-signal-passDim/30 px-3 py-1.5 text-xs text-signal-pass">
            Showing cached diagnosis. Click "Re-run diagnosis" if the case data has changed.
          </p>
        )}

        {!mockMode && modelUsed && !isCached && (
          <p
            className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs ${
              fallbackOccurred
                ? "border-signal-warn/25 bg-signal-warnDim/30 text-signal-warn"
                : "border-signal-info/25 bg-signal-infoDim/30 text-signal-info"
            }`}
          >
            <Sparkles size={12} />
            Answered by <span className="font-mono">{modelUsed}</span>
            {fallbackOccurred && " - the primary model's quota was exhausted, so this request automatically fell back to the next configured model."}
          </p>
        )}

        {diagnoseError && (
          <div className="rounded-md border border-signal-fail/30 bg-signal-failDim/40 px-3 py-2.5 text-sm text-signal-fail">
            {diagnoseError}
          </div>
        )}

        {diagnosis && (
          <AIDiagnosisCard
            diagnosis={diagnosis}
            showOutputs={caseData.show_outputs}
            evidenceHighlights={evidenceHighlights}
          />
        )}
      </section>

      {diagnosis && (
        <section className="space-y-3">
          {reviewError && (
            <div className="rounded-md border border-signal-fail/30 bg-signal-failDim/40 px-3 py-2.5 text-sm text-signal-fail">
              {reviewError}
            </div>
          )}
          <ReviewPanel
            caseId={caseData.case_id}
            diagnosis={diagnosis}
            onSubmit={handleReviewSubmit}
            submitting={submittingReview}
            lastDecision={lastDecision}
          />
        </section>
      )}

      {currentReview && (
        <section className="space-y-3">
          {verifyError && (
            <div className="rounded-md border border-signal-fail/30 bg-signal-failDim/40 px-3 py-2.5 text-sm text-signal-fail">
              {verifyError}
            </div>
          )}
          <VerificationPanel
            verificationCommand={caseData.verification_command}
            onVerify={handleVerifySubmit}
            submitting={verifying}
            status={currentReview.verification_status}
            evidenceMissed={currentReview.evidence_missed}
          />
        </section>
      )}
    </div>
  );
}
