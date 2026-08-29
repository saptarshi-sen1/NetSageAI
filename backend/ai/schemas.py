"""
Pydantic schemas for the AI diagnosis pipeline.

AIDiagnosis mirrors the exact JSON contract defined in
prompts/diagnose_prompt.md. Every field the LLM is asked to produce is
validated here; a malformed or missing field results in a
DiagnosisParseError being raised by backend/ai/diagnosis.py, which the
API layer turns into a clean error response instead of a crash.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

ConfidenceLabel = Literal["Low", "Medium", "High"]


class AIDiagnosis(BaseModel):
    root_cause: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_label: ConfidenceLabel
    osi_layer: str
    concept: str
    evidence: List[str] = Field(default_factory=list)
    reasoning_summary: str
    next_command: str = ""
    fix_steps: List[str] = Field(default_factory=list)
    verification_steps: List[str] = Field(default_factory=list)
    human_review_required: bool = True

    @field_validator("human_review_required")
    @classmethod
    def _force_human_review(cls, _v: bool) -> bool:
        # Defense in depth: regardless of what the model returns, this
        # field is always true. See docs/responsible_ai.md.
        return True


class DiagnoseRequest(BaseModel):
    case_id: str
    force: bool = False


class DiagnoseResponse(BaseModel):
    case_id: str
    ai_diagnosis: Optional[AIDiagnosis] = None
    error: Optional[str] = None
    mock_mode: bool = False
    matches_expected: Optional[bool] = None


class CheckRequest(BaseModel):
    case_id: str


class ReviewDecision(str):
    pass


DecisionLiteral = Literal["ACCEPTED", "EDITED", "REJECTED"]


class ReviewCreateRequest(BaseModel):
    case_id: str
    ai_root_cause: str = ""
    ai_confidence: float = 0.0
    human_decision: DecisionLiteral
    human_root_cause: str = ""
    correction_reason: str = ""
    reviewer: str = "Anonymous Reviewer"

    @model_validator(mode="after")
    def _require_reason_if_rejected(self) -> "ReviewCreateRequest":
        # A model-level (not field-level) validator is used here on
        # purpose: Pydantic v2 skips field_validators for fields left at
        # their default value unless validate_default=True is set, which
        # would silently let an omitted correction_reason slip through
        # on a REJECTED review. This check always runs.
        if self.human_decision == "REJECTED" and not self.correction_reason.strip():
            raise ValueError("correction_reason is required when human_decision is REJECTED")
        return self


VerificationStatus = Literal["VERIFIED", "VERIFICATION_FAILED", "NOT_VERIFIED"]


class ReviewVerifyRequest(BaseModel):
    verification_status: VerificationStatus
    evidence_missed: str = ""

    @model_validator(mode="after")
    def _require_evidence_if_failed(self) -> "ReviewVerifyRequest":
        if self.verification_status == "VERIFICATION_FAILED" and not self.evidence_missed.strip():
            raise ValueError("evidence_missed is required when verification_status is VERIFICATION_FAILED")
        return self
