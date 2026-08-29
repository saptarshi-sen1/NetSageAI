"""
Practice Mode service. Two responsibilities:

1. to_practice_view(case) - redact a case down to only the fields a
   student should see BEFORE answering (see practice_schemas.py's
   docstring for why this is a field whitelist, not a blacklist/delete).

2. submit_practice_attempt(...) - run a student's submitted hypothesis
   against: (a) the SAME deterministic rule checker every case uses,
   (b) the SAME diagnose() AI pipeline every case uses (no
   special-casing - a real GEMINI_API_KEY, if configured, is used here
   exactly as it is from /api/diagnose), and (c) the dataset's
   expected_* ground truth. Records the result as a COMPLETED attempt
   via attempt_service, so Practice Mode and the Student Workspace
   share one underlying history rather than two parallel systems.
"""
from __future__ import annotations

from backend.ai.diagnosis import diagnose
from backend.ai.evidence_highlighting import highlight_evidence
from backend.rules.checker import run_checks
from backend.services.attempt_service import complete_attempt, start_attempt
from backend.services.practice_schemas import (
    PracticeCaseView,
    PracticeComparisonResult,
)


def to_practice_view(case: dict) -> PracticeCaseView:
    return PracticeCaseView(
        case_id=case["case_id"],
        title=case["title"],
        symptom=case["symptom"],
        topology_note=case["topology_note"],
        show_outputs=case["show_outputs"],
        osi_layer=case["osi_layer"],
        concept=case["concept"],
        severity=case["severity"],
        difficulty=case["difficulty"],
    )


def _concept_matches(a: str, b: str) -> bool:
    """Same loose substring-match heuristic backend/ai/diagnosis.py's
    compare_to_expected() already uses for the (separate) AI-vs-expected
    comparison shown on the admin dashboard - reused here for
    consistency, applied to whichever text field is being compared."""
    a_norm = (a or "").strip().lower()
    b_norm = (b or "").strip().lower()
    if not a_norm or not b_norm:
        return False
    return a_norm in b_norm or b_norm in a_norm


def submit_practice_attempt(
    case: dict,
    student_name: str,
    student_root_cause: str,
    student_osi_layer: str,
    student_next_command: str,
    student_fix: str,
    ai_client=None,
) -> PracticeComparisonResult:
    """The student has already committed to their answer by the time
    this is called (enforced client-side by the UI not requesting a
    diagnosis until after submission, and server-side by this being the
    only endpoint that both accepts a student answer AND returns
    ground truth - see api/practice.py).

    `ai_client` is optional and passed through to diagnose() exactly
    like /api/diagnose does via its FastAPI dependency - see
    api/diagnosis.py::_resolve_ai_client's docstring. When None (the
    default), diagnose() falls back to get_ai_client()'s real
    environment-based provider selection, identical to production
    behavior. Tests pass an explicit MockAIClient here the same way
    tests/conftest.py does for /api/diagnose, so Practice Mode tests
    never make a live network call either."""

    # Record (or resume) the attempt first, so even if the AI call below
    # fails, the student's own answer is never lost.
    attempt = start_attempt(case["case_id"], student_name)

    rule_findings = run_checks(case)
    diagnosis_result = diagnose(case, ai_client=ai_client)

    ai_root_cause = None
    ai_confidence_label = None
    ai_osi_layer = None
    ai_evidence: list[str] = []
    ai_evidence_highlights = []
    ai_error = diagnosis_result.error

    if diagnosis_result.ai_diagnosis:
        ai_root_cause = diagnosis_result.ai_diagnosis.root_cause
        ai_confidence_label = diagnosis_result.ai_diagnosis.confidence_label
        ai_osi_layer = diagnosis_result.ai_diagnosis.osi_layer
        ai_evidence = diagnosis_result.ai_diagnosis.evidence
        if ai_evidence:
            ai_evidence_highlights = highlight_evidence(case["show_outputs"], ai_evidence)

    student_matches = _concept_matches(student_root_cause, case["expected_fault"])
    ai_matches = _concept_matches(ai_root_cause or "", case["expected_fault"]) if ai_root_cause else False

    completed = complete_attempt(
        attempt["attempt_id"],
        student_root_cause=student_root_cause,
        student_osi_layer=student_osi_layer,
        student_next_command=student_next_command,
        student_fix=student_fix,
        ai_root_cause=ai_root_cause or "",
        matches_expected_concept=student_matches,
    )

    return PracticeComparisonResult(
        attempt_id=completed["attempt_id"],
        case_id=case["case_id"],
        student_root_cause=student_root_cause,
        student_osi_layer=student_osi_layer,
        student_next_command=student_next_command,
        student_fix=student_fix,
        ai_root_cause=ai_root_cause,
        ai_confidence_label=ai_confidence_label,
        ai_osi_layer=ai_osi_layer,
        ai_evidence=ai_evidence,
        ai_evidence_highlights=ai_evidence_highlights,
        ai_error=ai_error,
        mock_mode=diagnosis_result.mock_mode,
        expected_fault=case["expected_fault"],
        expected_osi_layer=case["osi_layer"],
        expected_evidence=case["expected_evidence"],
        expected_next_command=case["expected_next_command"],
        expected_fix=case["expected_fix"],
        verification_command=case["verification_command"],
        student_matches_expected_concept=student_matches,
        ai_matches_expected_concept=ai_matches,
        rule_findings_count=len(rule_findings),
    )
