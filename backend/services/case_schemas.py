"""
Pydantic schemas for case management (create / update / archive).
Kept separate from backend/ai/schemas.py, which is specific to the AI
diagnosis pipeline's JSON contract - this module is plain CRUD.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Severity = Literal["Low", "Medium", "High", "Critical"]
Difficulty = Literal["Easy", "Medium", "Hard"]


class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    symptom: str = Field(..., min_length=1)
    topology_note: str = Field(..., min_length=1)
    show_outputs: str = Field(..., min_length=1)
    expected_fault: str = Field(..., min_length=1)
    osi_layer: str = Field(..., min_length=1)
    concept: str = Field(..., min_length=1)
    severity: Severity
    expected_evidence: str = ""
    expected_next_command: str = ""
    expected_fix: str = ""
    verification_command: str = ""
    difficulty: Difficulty = "Medium"
    created_by: str = "Anonymous"

    @field_validator(
        "title", "symptom", "topology_note", "show_outputs",
        "expected_fault", "osi_layer", "concept",
    )
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field cannot be blank.")
        return v


class CaseUpdateRequest(BaseModel):
    """Every field optional - only fields actually provided are changed.
    Same validation rules as create when a field IS provided."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    symptom: Optional[str] = Field(None, min_length=1)
    topology_note: Optional[str] = Field(None, min_length=1)
    show_outputs: Optional[str] = Field(None, min_length=1)
    expected_fault: Optional[str] = Field(None, min_length=1)
    osi_layer: Optional[str] = Field(None, min_length=1)
    concept: Optional[str] = Field(None, min_length=1)
    severity: Optional[Severity] = None
    expected_evidence: Optional[str] = None
    expected_next_command: Optional[str] = None
    expected_fix: Optional[str] = None
    verification_command: Optional[str] = None
    difficulty: Optional[Difficulty] = None


class CaseStatusUpdateRequest(BaseModel):
    status: Literal["active", "archived"]
