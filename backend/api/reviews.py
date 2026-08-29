from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from backend.ai.schemas import ReviewCreateRequest, ReviewVerifyRequest
from backend.services.review_service import ReviewNotFoundError, create_review, list_reviews, verify_review

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("")
def get_reviews():
    return {"reviews": list_reviews()}


@router.post("")
def post_review(payload: ReviewCreateRequest):
    """Record a human's ACCEPT / EDIT / REJECT decision on an AI
    diagnosis. This is the only mutation the AI pipeline can ever
    trigger indirectly - and it always requires an explicit human
    decision to reach this endpoint in the first place."""
    try:
        review = create_review(
            case_id=payload.case_id,
            ai_root_cause=payload.ai_root_cause,
            ai_confidence=payload.ai_confidence,
            human_decision=payload.human_decision,
            human_root_cause=payload.human_root_cause,
            correction_reason=payload.correction_reason,
            reviewer=payload.reviewer,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"review": review}


@router.patch("/{review_id}/verify")
def patch_verify_review(review_id: str, payload: ReviewVerifyRequest):
    """Update a review's verification status (VERIFIED or VERIFICATION_FAILED)."""
    try:
        review = verify_review(
            review_id=review_id,
            status=payload.verification_status,
            evidence_missed=payload.evidence_missed,
        )
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"review": review}
