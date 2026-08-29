export type CaseStatus = "active" | "archived";
export type CaseSource = "seed" | "user";

export interface Case {
  case_id: string;
  title: string;
  symptom: string;
  topology_note: string;
  show_outputs: string;
  expected_fault: string;
  osi_layer: string;
  concept: string;
  severity: "Low" | "Medium" | "High" | "Critical";
  expected_evidence: string;
  expected_next_command: string;
  expected_fix: string;
  verification_command: string;
  difficulty: "Easy" | "Medium" | "Hard";
  status: CaseStatus;
  source: CaseSource;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface CaseFacets {
  concepts: string[];
  severities: string[];
  osi_layers: string[];
  difficulties: string[];
}

export interface CaseListParams {
  concept?: string;
  severity?: string;
  osi_layer?: string;
  difficulty?: string;
  search?: string;
  include_archived?: boolean;
}

/** Fields the create/edit form actually submits. Mirrors
 * backend/services/case_schemas.py::CaseCreateRequest exactly. */
export interface CaseFormFields {
  title: string;
  symptom: string;
  topology_note: string;
  show_outputs: string;
  expected_fault: string;
  osi_layer: string;
  concept: string;
  severity: "Low" | "Medium" | "High" | "Critical";
  expected_evidence: string;
  expected_next_command: string;
  expected_fix: string;
  verification_command: string;
  difficulty: "Easy" | "Medium" | "Hard";
}

export interface CaseCreateRequest extends CaseFormFields {
  created_by?: string;
}

export type CaseUpdateRequest = Partial<CaseFormFields>;

export type FindingStatus = "PASS" | "FAIL" | "WARN";
export type FindingSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Finding {
  rule: string;
  status: FindingStatus;
  severity: FindingSeverity;
  evidence: string;
  message: string;
}

export type ConfidenceLabel = "Low" | "Medium" | "High";

export interface AIDiagnosis {
  root_cause: string;
  confidence: number;
  confidence_label: ConfidenceLabel;
  osi_layer: string;
  concept: string;
  evidence: string[];
  reasoning_summary: string;
  next_command: string;
  fix_steps: string[];
  verification_steps: string[];
  human_review_required: true;
}

export interface EvidenceSpan {
  start: number;
  end: number;
  text: string;
}

export interface EvidenceHighlight {
  evidence_text: string;
  spans: EvidenceSpan[];
}

export interface DiagnoseResponse {
  case_id: string;
  mock_mode: boolean;
  model_used: string | null;
  fallback_occurred: boolean;
  rule_findings: Finding[];
  ai_diagnosis: AIDiagnosis | null;
  evidence_highlights: EvidenceHighlight[] | null;
  error: string | null;
  cached: boolean;
  human_review_required: true;
  safety_notice: string;
}

export interface CheckResponse {
  case_id: string;
  findings: Finding[];
}

export type ReviewDecision = "ACCEPTED" | "EDITED" | "REJECTED";

export interface Review {
  review_id: string;
  case_id: string;
  ai_root_cause: string;
  ai_confidence: string | number;
  human_decision: ReviewDecision;
  human_root_cause: string;
  correction_reason: string;
  reviewer: string;
  timestamp: string;
  verification_status: "VERIFIED" | "VERIFICATION_FAILED" | "NOT_VERIFIED";
  evidence_missed: string;
}

export interface ReviewCreateRequest {
  case_id: string;
  ai_root_cause?: string;
  ai_confidence?: number;
  human_decision: ReviewDecision;
  human_root_cause?: string;
  correction_reason?: string;
  reviewer?: string;
}

export interface ReviewVerifyPayload {
  verification_status: "VERIFIED" | "VERIFICATION_FAILED" | "NOT_VERIFIED";
  evidence_missed?: string;
}

export interface DashboardData {
  total_cases: number;
  cases_by_concept: Record<string, number>;
  cases_by_severity: Record<string, number>;
  cases_by_osi_layer: Record<string, number>;
  reviewed: number;
  decision_counts: Record<ReviewDecision, number>;
  agreement_rate_percent: number;
  average_ai_confidence: number;
  corrections_by_concept: Record<string, number>;
  corrections_by_severity: Record<string, number>;
  rule_hit_counts: Record<string, number>;
  recent_reviews: Review[];
  student_progress: {
    case_id: string;
    total_attempts: number;
    completed: number;
    successful: number;
    success_rate_percent: number;
  }[];
  safety_notice: string;
}

// --------------------------------------------------------------------------
// Student Workspace
// --------------------------------------------------------------------------
export type AttemptStatus = "IN_PROGRESS" | "COMPLETED";
export type CaseProgressStatus = "not_started" | "in_progress" | "completed";

export interface Attempt {
  attempt_id: string;
  case_id: string;
  student_name: string;
  status: AttemptStatus;
  started_at: string;
  completed_at: string;
  student_root_cause: string;
  student_osi_layer: string;
  student_next_command: string;
  student_fix: string;
  ai_root_cause: string;
  matches_expected_concept: string;
}

export interface AttemptCompletePayload {
  student_root_cause?: string;
  student_osi_layer?: string;
  student_next_command?: string;
  student_fix?: string;
  ai_root_cause?: string;
  matches_expected_concept?: boolean;
}

export interface ConceptProgress {
  total: number;
  attempted: number;
  completed: number;
}

export interface WorkspaceSummary {
  student_name: string;
  total_available_cases: number;
  attempted_count: number;
  completed_count: number;
  in_progress_count: number;
  attempted_case_ids: string[];
  completed_case_ids: string[];
  in_progress_case_ids: string[];
  practice_by_concept: Record<string, ConceptProgress>;
  safety_notice: string;
}

export interface CaseStatusMap {
  case_status: Record<string, CaseProgressStatus>;
}

// --------------------------------------------------------------------------
// Practice Mode
// --------------------------------------------------------------------------
/** The redacted, pre-answer view of a case for Practice Mode. Mirrors
 * backend/services/practice_schemas.py::PracticeCaseView exactly - it
 * intentionally has NO expected_fault/expected_fix/expected_evidence/
 * expected_next_command/verification_command fields, because the
 * backend itself never sends them until after submission. */
export interface PracticeCaseView {
  case_id: string;
  title: string;
  symptom: string;
  topology_note: string;
  show_outputs: string;
  osi_layer: string;
  concept: string;
  severity: string;
  difficulty: string;
}

export interface PracticeSubmitPayload {
  case_id: string;
  student_name?: string;
  student_root_cause: string;
  student_osi_layer?: string;
  student_next_command?: string;
  student_fix?: string;
}

export interface PracticeComparisonResult {
  attempt_id: string;
  case_id: string;

  student_root_cause: string;
  student_osi_layer: string;
  student_next_command: string;
  student_fix: string;

  ai_root_cause: string | null;
  ai_confidence_label: ConfidenceLabel | null;
  ai_osi_layer: string | null;
  ai_evidence: string[];
  ai_evidence_highlights: EvidenceHighlight[];
  ai_error: string | null;
  mock_mode: boolean;

  expected_fault: string;
  expected_osi_layer: string;
  expected_evidence: string;
  expected_next_command: string;
  expected_fix: string;
  verification_command: string;

  student_matches_expected_concept: boolean;
  ai_matches_expected_concept: boolean;

  rule_findings_count: number;
  human_review_required: true;
  safety_notice: string;
}
