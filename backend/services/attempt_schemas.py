"""
Pydantic schemas for the Student Workspace attempt-tracking endpoints.
Kept separate from ai/schemas.py (diagnosis pipeline) and
case_schemas.py (case CRUD) - this is a third, distinct concern.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AttemptStartRequest(BaseModel):
    case_id: str = Field(..., min_length=1)
    student_name: str = Field(default="Anonymous", max_length=100)


class AttemptCompleteRequest(BaseModel):
    student_root_cause: str = ""
    student_osi_layer: str = ""
    student_next_command: str = ""
    student_fix: str = ""
    ai_root_cause: str = ""
    matches_expected_concept: Optional[bool] = None
