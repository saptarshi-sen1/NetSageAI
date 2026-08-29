from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.ai.client import AIClient
from backend.api.diagnosis import _resolve_ai_client
from backend.services.case_service import CaseNotFoundError, get_case
from backend.services.practice_schemas import PracticeComparisonResult, PracticeSubmitRequest
from backend.services.practice_service import submit_practice_attempt, to_practice_view

router = APIRouter(prefix="/api/practice", tags=["practice"])


@router.get("/cases/{case_id}")
def get_practice_case(case_id: str):
    """The redacted, pre-answer view of a case for Practice Mode. Never
    includes expected_fault, expected_evidence, expected_next_command,
    expected_fix, or verification_command - see
    practice_service.py::to_practice_view and practice_schemas.py's
    module docstring for the whitelist-not-blacklist safety property."""
    try:
        case = get_case(case_id)
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return to_practice_view(case)


@router.post("/submit", response_model=PracticeComparisonResult)
def post_practice_submit(
    payload: PracticeSubmitRequest,
    ai_client: AIClient = Depends(_resolve_ai_client),
):
    """The student has already committed to their hypothesis by calling
    this endpoint - only AFTER this call does the response include the
    AI's diagnosis and the dataset's expected answer. Runs the exact
    same rule checker and diagnose() pipeline as every other case (via
    the same ai_client dependency /api/diagnose uses), so a real
    configured provider (Gemini) is used here identically - no
    special-casing for Practice Mode."""
    try:
        case = get_case(payload.case_id)
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case '{payload.case_id}' not found")

    result = submit_practice_attempt(
        case,
        student_name=payload.student_name,
        student_root_cause=payload.student_root_cause,
        student_osi_layer=payload.student_osi_layer,
        student_next_command=payload.student_next_command,
        student_fix=payload.student_fix,
        ai_client=ai_client,
    )
    return result
