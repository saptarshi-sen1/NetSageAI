from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.ai.client import AIClient, get_ai_client
from backend.ai.diagnosis import diagnose
from backend.ai.evidence_highlighting import highlight_evidence
from backend.ai.schemas import CheckRequest, DiagnoseRequest
from backend.rules.checker import run_checks
from backend.services.case_service import CaseNotFoundError, get_case
import backend.services.diagnosis_cache as diagnosis_cache

router = APIRouter(prefix="/api", tags=["diagnosis"])


def _resolve_ai_client() -> AIClient:
    """FastAPI dependency wrapping get_ai_client(). Exists so tests can
    override *which client this endpoint uses* via
    app.dependency_overrides[_resolve_ai_client], WITHOUT touching
    get_ai_client()'s real environment-based provider selection logic
    at all. This is what lets the test suite be environment-aware:
    - Tests that want to verify mock-mode behavior override this
      dependency to force a MockAIClient, regardless of whether a real
      GEMINI_API_KEY happens to be set in the environment the test
      suite runs in (e.g. a developer's real .env).
    - Tests that want to verify real-provider selection (see
      tests/test_provider_selection.py) call get_ai_client() directly
      instead of going through the API, so they can assert on which
      client class was constructed without making a live network call.
    - Production code (no override installed) calls get_ai_client()
      exactly as before - nothing about real Gemini behavior changes
      for actual users.
    """
    return get_ai_client()


@router.post("/check")
def check_case(payload: CheckRequest):
    """Run ONLY the deterministic rule checker against a case - no AI
    call, no cost, always available even with zero API key configured."""
    try:
        case = get_case(payload.case_id)
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case '{payload.case_id}' not found")

    findings = run_checks(case)
    return {
        "case_id": payload.case_id,
        "findings": [f.to_dict() for f in findings],
    }


@router.post("/diagnose")
def diagnose_case(payload: DiagnoseRequest, ai_client: AIClient = Depends(_resolve_ai_client)):
    """Run the deterministic checker AND the AI diagnosis pipeline. The
    response always includes a `human_review_required: true` banner
    field, in addition to whatever the AI itself set on its diagnosis,
    as an extra layer of defense-in-depth."""
    try:
        case = get_case(payload.case_id)
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case '{payload.case_id}' not found")

    cached_result = None
    if not payload.force:
        cached_result = diagnosis_cache.get_cached(payload.case_id)

    if cached_result and not cached_result.error:
        result = cached_result
    else:
        result = diagnose(case, ai_client=ai_client)
        if not result.error:
            diagnosis_cache.save_to_cache(payload.case_id, result)

    evidence_highlights = None
    if result.ai_diagnosis and result.ai_diagnosis.evidence:
        evidence_highlights = [
            h.model_dump()
            for h in highlight_evidence(case["show_outputs"], result.ai_diagnosis.evidence)
        ]

    response = {
        "case_id": payload.case_id,
        "mock_mode": result.mock_mode,
        "model_used": result.model_used,
        "fallback_occurred": result.fallback_occurred,
        "rule_findings": [f.to_dict() for f in result.rule_findings],
        "ai_diagnosis": result.ai_diagnosis.model_dump() if result.ai_diagnosis else None,
        "evidence_highlights": evidence_highlights,
        "error": result.error,
        "cached": bool(cached_result),
        "human_review_required": True,
        "safety_notice": (
            "AI recommendations are suggestions and must be reviewed by "
            "a human before implementation."
        ),
    }
    return response
