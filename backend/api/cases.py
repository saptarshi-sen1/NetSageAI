from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.services.case_schemas import (
    CaseCreateRequest,
    CaseStatusUpdateRequest,
    CaseUpdateRequest,
)
from backend.services.case_service import (
    CaseNotFoundError,
    create_case,
    distinct_facet_values,
    get_case,
    list_cases,
    set_case_status,
    update_case,
)

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
def get_cases(
    concept: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    osi_layer: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    include_archived: bool = Query(False),
):
    """List cases. With no query parameters, behaves exactly as before
    (all active cases, full rows - summary-only pagination would be an
    optimization not needed at this dataset size). Every filter is
    optional and combines with AND; `search` matches case_id, title, or
    symptom (case-insensitive substring)."""
    return {
        "cases": list_cases(
            concept=concept,
            severity=severity,
            osi_layer=osi_layer,
            difficulty=difficulty,
            search=search,
            include_archived=include_archived,
        )
    }


@router.get("/facets")
def get_case_facets():
    """Distinct concept/severity/osi_layer/difficulty values across
    active cases, so the frontend can populate filter dropdowns without
    fetching and deriving them from the full case list.

    IMPORTANT: this route must stay registered BEFORE GET /{case_id}
    below. FastAPI/Starlette match routes in registration order, so if
    /{case_id} were registered first, a request to /api/cases/facets
    would be swallowed by it (case_id="facets") and return 404 instead
    of ever reaching this handler."""
    return distinct_facet_values()


@router.post("")
def post_case(payload: CaseCreateRequest):
    """Create a new troubleshooting case. It is persisted to
    data/cases.csv and immediately available via GET /api/cases and
    GET /api/cases/{case_id} - meaning it works through the identical
    Rule Checker -> AI Diagnosis -> Human Review -> Verification
    pipeline as every seed case with zero extra plumbing, since that
    pipeline only ever reads cases through get_case()."""
    fields = payload.model_dump(exclude={"created_by"})
    case = create_case(fields, created_by=payload.created_by)
    return {"case": case}


@router.get("/{case_id}")
def get_case_detail(case_id: str):
    try:
        return get_case(case_id)
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")


@router.patch("/{case_id}")
def patch_case(case_id: str, payload: CaseUpdateRequest):
    """Update an existing case's content fields. Only fields present in
    the request body are changed - case_id, source, and created_at are
    never mutated here."""
    fields = payload.model_dump(exclude_unset=True)
    try:
        case = update_case(case_id, fields)
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return {"case": case}


@router.patch("/{case_id}/status")
def patch_case_status(case_id: str, payload: CaseStatusUpdateRequest):
    """Archive or restore a case (soft delete - see case_service.py
    module docstring for why rows are never physically removed)."""
    try:
        case = set_case_status(case_id, payload.status)
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return {"case": case}
