"""
Shared data model for the deterministic rule checker.

IMPORTANT: nothing in this module (or anywhere under backend/rules/)
calls an LLM. Every check here is a plain string/regex inspection of
the `show` command output supplied for a case. Same input always
produces the same output - that determinism is the whole point of
this layer, and it's what the AI diagnosis is cross-checked against.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["PASS", "FAIL", "WARN"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class Finding(BaseModel):
    """A single deterministic rule-checker result."""

    rule: str = Field(..., description="Machine-readable rule identifier, e.g. 'missing_route'")
    status: Status = Field(..., description="PASS, FAIL, or WARN")
    severity: Severity = Field(..., description="Impact if this finding indicates a real fault")
    evidence: str = Field(..., description="The literal text/output this finding was derived from")
    message: str = Field(..., description="Human-readable explanation of the finding")

    def to_dict(self) -> dict:
        return self.model_dump()
