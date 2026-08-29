"""
Pydantic schemas for Practice Mode.

The key safety property of this whole module: PracticeCaseView is
constructed by explicitly whitelisting fields (see
practice_service.py::to_practice_view), never by taking a full Case and
trying to delete keys from it. That whitelist approach means adding a
new ground-truth field to the Case model later can't accidentally leak
through Practice Mode by omission - a new field has to be deliberately
added to this schema to ever reach a student before they've submitted
an answer.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from backend.ai.evidence_highlighting import EvidenceHighlight


class PracticeCaseView(BaseModel):
    """Everything a student is allowed to see BEFORE submitting their
    hypothesis. Deliberately excludes expected_fault, expected_evidence,
    expected_next_command, expected_fix, and verification_command."""

    case_id: str
    title: str
    symptom: str
    topology_note: str
    show_outputs: str
    osi_layer: str
    concept: str
    severity: str
    difficulty: str


class PracticeSubmitRequest(BaseModel):
    case_id: str = Field(..., min_length=1)
    student_name: str = Field(default="Anonymous", max_length=100)
    student_root_cause: str = Field(..., min_length=1)
    student_osi_layer: str = Field(default="")
    student_next_command: str = Field(default="")
    student_fix: str = Field(default="")

    @field_validator("case_id", "student_root_cause")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        # min_length=1 alone accepts whitespace-only strings like "   "
        # (they have length 1+) - this closes that gap the same way
        # case_schemas.py::CaseCreateRequest._not_blank does, so a
        # student can't "submit" an empty answer that merely contains
        # spaces and have it silently accepted.
        if not v.strip():
            raise ValueError("This field cannot be blank.")
        return v


class PracticeComparisonResult(BaseModel):
    """The feedback shown after a student submits - the whole point of
    Practice Mode. Includes the AI's independent diagnosis (run through
    the exact same pipeline as every other case, no special-casing) and
    the dataset's expected answer, now that the student has committed
    to their own answer first."""

    attempt_id: str
    case_id: str

    student_root_cause: str
    student_osi_layer: str
    student_next_command: str
    student_fix: str

    ai_root_cause: Optional[str] = None
    ai_confidence_label: Optional[str] = None
    ai_osi_layer: Optional[str] = None
    ai_evidence: List[str] = Field(default_factory=list)
    ai_evidence_highlights: List[EvidenceHighlight] = Field(default_factory=list)
    ai_error: Optional[str] = None
    mock_mode: bool = False

    expected_fault: str
    expected_osi_layer: str
    expected_evidence: str
    expected_next_command: str
    expected_fix: str
    verification_command: str

    student_matches_expected_concept: bool
    ai_matches_expected_concept: bool

    rule_findings_count: int
    human_review_required: bool = True
    safety_notice: str = (
        "AI recommendations are advisory. A human reviewer must approve "
        "every diagnosis before a fix is accepted. This comparison is a "
        "learning aid, not a graded verdict - use your own judgment "
        "alongside it."
    )
