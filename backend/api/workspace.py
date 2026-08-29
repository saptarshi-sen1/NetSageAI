from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.services.attempt_schemas import AttemptCompleteRequest, AttemptStartRequest
from backend.services.attempt_service import (
    AttemptNotFoundError,
    complete_attempt,
    list_attempts_for_student,
    start_attempt,
    student_summary,
)
from backend.services.case_service import list_cases, summary_counts

router = APIRouter(prefix="/api", tags=["workspace"])


@router.post("/attempts/start")
def post_start_attempt(payload: AttemptStartRequest):
    """Record that a student opened a case in the workspace. Idempotent
    per (case, student) while an attempt is IN_PROGRESS - re-opening a
    case you haven't finished doesn't create duplicate attempts."""
    attempt = start_attempt(payload.case_id, payload.student_name)
    return {"attempt": attempt}


@router.post("/attempts/{attempt_id}/complete")
def post_complete_attempt(attempt_id: str, payload: AttemptCompleteRequest):
    try:
        attempt = complete_attempt(
            attempt_id,
            student_root_cause=payload.student_root_cause,
            student_osi_layer=payload.student_osi_layer,
            student_next_command=payload.student_next_command,
            student_fix=payload.student_fix,
            ai_root_cause=payload.ai_root_cause,
            matches_expected_concept=payload.matches_expected_concept,
        )
    except AttemptNotFoundError:
        raise HTTPException(status_code=404, detail=f"Attempt '{attempt_id}' not found")
    return {"attempt": attempt}


@router.get("/attempts")
def get_attempts(student_name: str = Query(..., min_length=1)):
    return {"attempts": list_attempts_for_student(student_name)}


@router.get("/workspace/summary")
def get_workspace_summary(student_name: str = Query(..., min_length=1)):
    """Everything the Student Workspace dashboard needs in one call:
    total available cases, this student's attempted/completed/
    in-progress counts, and practice-case counts broken down by
    concept - so a student can see where they still need practice."""
    active_cases = list_cases()
    case_summary = summary_counts()
    progress = student_summary(student_name)

    attempted_set = set(progress["attempted_case_ids"])
    completed_set = set(progress["completed_case_ids"])

    by_concept = {}
    for concept, total in case_summary["by_concept"].items():
        concept_case_ids = {c["case_id"] for c in active_cases if c["concept"] == concept}
        by_concept[concept] = {
            "total": total,
            "attempted": len(concept_case_ids & attempted_set),
            "completed": len(concept_case_ids & completed_set),
        }

    return {
        "student_name": student_name,
        "total_available_cases": len(active_cases),
        "attempted_count": progress["attempted_count"],
        "completed_count": progress["completed_count"],
        "in_progress_count": len(progress["in_progress_case_ids"]),
        "attempted_case_ids": progress["attempted_case_ids"],
        "completed_case_ids": progress["completed_case_ids"],
        "in_progress_case_ids": progress["in_progress_case_ids"],
        "practice_by_concept": by_concept,
        "safety_notice": (
            "AI recommendations are advisory. A human reviewer must "
            "approve every diagnosis before a fix is accepted."
        ),
    }


@router.get("/workspace/case-status")
def get_case_status_for_student(student_name: str = Query(..., min_length=1)):
    """Per-case status map (not_started / in_progress / completed) for
    every active case, keyed by case_id - lets the Student Workspace
    case grid show a badge on every card without N separate requests."""
    active_cases = list_cases()
    progress = student_summary(student_name)
    attempted = set(progress["attempted_case_ids"])
    completed = set(progress["completed_case_ids"])

    status_map = {}
    for c in active_cases:
        if c["case_id"] in completed:
            status_map[c["case_id"]] = "completed"
        elif c["case_id"] in attempted:
            status_map[c["case_id"]] = "in_progress"
        else:
            status_map[c["case_id"]] = "not_started"
    return {"case_status": status_map}
