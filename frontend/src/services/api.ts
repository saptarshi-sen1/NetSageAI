import type {
  Attempt,
  AttemptCompletePayload,
  Case,
  CaseCreateRequest,
  CaseFacets,
  CaseListParams,
  CaseStatus,
  CaseStatusMap,
  CaseUpdateRequest,
  CheckResponse,
  DashboardData,
  DiagnoseResponse,
  PracticeCaseView,
  PracticeComparisonResult,
  PracticeSubmitPayload,
  Review,
  ReviewCreateRequest,
  ReviewVerifyPayload,
  WorkspaceSummary,
} from "./types";

// In dev, Vite proxies /api/* to the FastAPI backend (see vite.config.ts).
// In production, set VITE_API_BASE_URL to the deployed backend's origin.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // response wasn't JSON - fall back to statusText
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export const api = {
  listCases: (params?: CaseListParams) => {
    const query = new URLSearchParams();
    if (params?.concept) query.set("concept", params.concept);
    if (params?.severity) query.set("severity", params.severity);
    if (params?.osi_layer) query.set("osi_layer", params.osi_layer);
    if (params?.difficulty) query.set("difficulty", params.difficulty);
    if (params?.search) query.set("search", params.search);
    if (params?.include_archived) query.set("include_archived", "true");
    const qs = query.toString();
    return request<{ cases: Case[] }>(`/api/cases${qs ? `?${qs}` : ""}`).then((r) => r.cases);
  },

  getCase: (caseId: string) => request<Case>(`/api/cases/${encodeURIComponent(caseId)}`),

  getCaseFacets: () => request<CaseFacets>("/api/cases/facets"),

  createCase: (payload: CaseCreateRequest) =>
    request<{ case: Case }>("/api/cases", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((r) => r.case),

  updateCase: (caseId: string, payload: CaseUpdateRequest) =>
    request<{ case: Case }>(`/api/cases/${encodeURIComponent(caseId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }).then((r) => r.case),

  setCaseStatus: (caseId: string, status: CaseStatus) =>
    request<{ case: Case }>(`/api/cases/${encodeURIComponent(caseId)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }).then((r) => r.case),

  runCheck: (caseId: string) =>
    request<CheckResponse>("/api/check", {
      method: "POST",
      body: JSON.stringify({ case_id: caseId }),
    }),

  runDiagnose: (caseId: string, force: boolean = false) =>
    request<DiagnoseResponse>("/api/diagnose", {
      method: "POST",
      body: JSON.stringify({ case_id: caseId, force }),
    }),

  listReviews: () => request<{ reviews: Review[] }>("/api/reviews").then((r) => r.reviews),

  submitReview: (payload: ReviewCreateRequest) =>
    request<{ review: Review }>("/api/reviews", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((r) => r.review),

  verifyReview: (reviewId: string, payload: ReviewVerifyPayload) =>
    request<{ review: Review }>(`/api/reviews/${encodeURIComponent(reviewId)}/verify`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }).then((r) => r.review),

  getDashboard: () => request<DashboardData>("/api/dashboard"),

  // Student Workspace
  startAttempt: (caseId: string, studentName: string) =>
    request<{ attempt: Attempt }>("/api/attempts/start", {
      method: "POST",
      body: JSON.stringify({ case_id: caseId, student_name: studentName }),
    }).then((r) => r.attempt),

  completeAttempt: (attemptId: string, payload: AttemptCompletePayload = {}) =>
    request<{ attempt: Attempt }>(`/api/attempts/${encodeURIComponent(attemptId)}/complete`, {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((r) => r.attempt),

  listAttempts: (studentName: string) =>
    request<{ attempts: Attempt[] }>(
      `/api/attempts?student_name=${encodeURIComponent(studentName)}`
    ).then((r) => r.attempts),

  getWorkspaceSummary: (studentName: string) =>
    request<WorkspaceSummary>(
      `/api/workspace/summary?student_name=${encodeURIComponent(studentName)}`
    ),

  getCaseStatusMap: (studentName: string) =>
    request<CaseStatusMap>(
      `/api/workspace/case-status?student_name=${encodeURIComponent(studentName)}`
    ).then((r) => r.case_status),

  // Practice Mode
  getPracticeCase: (caseId: string) =>
    request<PracticeCaseView>(`/api/practice/cases/${encodeURIComponent(caseId)}`),

  submitPractice: (payload: PracticeSubmitPayload) =>
    request<PracticeComparisonResult>("/api/practice/submit", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
