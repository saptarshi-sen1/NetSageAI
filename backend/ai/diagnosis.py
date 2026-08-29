"""
NetSage AI - Diagnosis Orchestration Pipeline

    Case
     |
     v
    Normalize input           (build_user_prompt)
     |
     v
    Deterministic rule checker (backend/rules/checker.py - run separately,
     |                          BEFORE this module, and shown alongside)
     v
    Send case + evidence + rule findings to the AI    (this module)
     |
     v
    Validate AI JSON           (AIDiagnosis pydantic model)
     |
     v
    (Compare against expected diagnosis - optional, informational only)
     |
     v
    Return to caller -> human reviewer

This module NEVER lets a malformed AI response crash the application.
If the model returns invalid JSON or a schema violation, diagnose()
returns a DiagnosisResult with `error` set instead of raising, so the
API layer can surface a clean message.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from backend.ai.client import AIClient, AIClientError, get_ai_client
from backend.ai.schemas import AIDiagnosis
from backend.rules.checker import build_evidence_text, run_checks
from backend.rules.models import Finding

SYSTEM_PROMPT = """You are NetSage AI, a network troubleshooting ASSISTANT for a Cisco \
Packet Tracer networking course. You help students and junior engineers \
connect a symptom to a likely root cause using ONLY the evidence they \
give you.

You are not an autonomous network administrator. You never claim to \
have made a change, and you never instruct the reader to treat your \
output as final. A qualified human always reviews your diagnosis before \
anything is implemented.

Rules you MUST follow:
1. EVIDENCE FIRST. Base your root cause only on the symptom, topology note, \
and show-command output actually provided. Do not invent interfaces, IP \
addresses, VLANs, routes, ACL entries, or command output not given to you.
2. DISTINGUISH OBSERVATION FROM INFERENCE. In `evidence`, only list facts \
that literally appear in the provided show output.
3. CALIBRATE CONFIDENCE (0.0-1.0) and a matching confidence_label of \
"Low", "Medium", or "High". Use High (>=0.8) only when evidence directly \
and unambiguously demonstrates the fault.
4. IF EVIDENCE IS INSUFFICIENT, lower confidence and populate next_command \
with the single most useful next command instead of guessing.
5. NEVER PRESENT UNCERTAIN DIAGNOSES AS FACT.
6. ALWAYS set "human_review_required": true.
7. Respond with ONLY a single valid JSON object, no prose, no Markdown \
fences, matching this schema exactly:

{
  "root_cause": string,
  "confidence": number,
  "confidence_label": "Low" | "Medium" | "High",
  "osi_layer": string,
  "concept": string,
  "evidence": string[],
  "reasoning_summary": string,
  "next_command": string,
  "fix_steps": string[],
  "verification_steps": string[],
  "human_review_required": true
}
"""


@dataclass
class DiagnosisResult:
    case_id: str
    ai_diagnosis: Optional[AIDiagnosis]
    rule_findings: List[Finding]
    mock_mode: bool
    error: Optional[str] = None
    raw_response: Optional[str] = None
    model_used: Optional[str] = None
    fallback_occurred: bool = False


def build_user_prompt(case: dict, rule_findings: List[Finding]) -> str:
    """Build the user-turn prompt: the case evidence plus deterministic
    rule-checker findings, so the AI can use (but must not blindly trust)
    what the deterministic layer already found.

    The case is embedded between CASE_JSON_START/CASE_JSON_END markers.
    This is also how MockAIClient recovers the case to build a
    deterministic offline response - see client.py."""
    case_payload = {
        "case_id": case.get("case_id"),
        "title": case.get("title"),
        "symptom": case.get("symptom"),
        "topology_note": case.get("topology_note"),
        "show_outputs": case.get("show_outputs"),
        # NOTE: expected_fault / expected_evidence / expected_fix /
        # verification_command / expected_next_command are intentionally
        # withheld here - the AI must reach its own conclusion from raw
        # evidence, the same as a human would. Ground truth is used only
        # for offline dataset accuracy checks, never sent to the model.
        "difficulty": case.get("difficulty"),
    }
    findings_payload = [f.to_dict() for f in rule_findings]

    return (
        "Diagnose the following networking case using only the evidence "
        "provided. Deterministic rule-checker findings are included as a "
        "second, independent source of evidence - use them if relevant, "
        "but reach your own conclusion; do not simply restate them.\n\n"
        "CASE_JSON_START\n"
        f"{json.dumps(case_payload, indent=2)}\n"
        "CASE_JSON_END\n\n"
        "DETERMINISTIC_RULE_FINDINGS_START\n"
        f"{json.dumps(findings_payload, indent=2)}\n"
        "DETERMINISTIC_RULE_FINDINGS_END\n"
    )


def _extract_json_object(raw: str) -> str:
    """Best-effort extraction of a JSON object from a raw model response,
    tolerating stray Markdown code fences or leading/trailing prose that
    a model might add despite instructions not to."""
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if fence_match:
        return fence_match.group(1)

    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return raw[first_brace : last_brace + 1]

    return raw


def parse_ai_response(raw: str) -> AIDiagnosis:
    """Parse and validate a raw model response into an AIDiagnosis.
    Raises ValueError/json.JSONDecodeError on failure - callers must
    catch these; see diagnose() below for the safe wrapper."""
    candidate = _extract_json_object(raw)
    data = json.loads(candidate)
    diagnosis = AIDiagnosis.model_validate(data)
    return diagnosis


def compare_to_expected(case: dict, diagnosis: AIDiagnosis) -> bool:
    """Lightweight, informational-only comparison against the dataset's
    ground truth, used for offline accuracy metrics (see tests/ and the
    dashboard's 'AI vs Human agreement' stats). This is NEVER shown to
    the human reviewer before they make a decision, to avoid anchoring
    their judgment on it."""
    expected_concept = (case.get("concept") or "").strip().lower()
    ai_concept = (diagnosis.concept or "").strip().lower()
    if expected_concept and ai_concept:
        return expected_concept in ai_concept or ai_concept in expected_concept
    return False


def diagnose(case: dict, ai_client: Optional[AIClient] = None) -> DiagnosisResult:
    """Run the full pipeline for a single case: deterministic checks,
    then AI diagnosis, with graceful handling of any AI failure."""
    client = ai_client or get_ai_client()

    rule_findings = run_checks(case)
    user_prompt = build_user_prompt(case, rule_findings)

    try:
        # `case` is passed through for MockAIClient's convenience only -
        # real provider clients ignore it and only ever see the prompts,
        # exactly like a real deployment. See AIClient.complete() docstring.
        raw = client.complete(SYSTEM_PROMPT, user_prompt, case=case)
    except AIClientError as exc:
        return DiagnosisResult(
            case_id=case.get("case_id", ""),
            ai_diagnosis=None,
            rule_findings=rule_findings,
            mock_mode=client.is_mock,
            error=f"AI provider error: {exc}",
        )

    # Populated by GeminiAIClient/MockAIClient after a successful
    # complete() call - lets the API/UI show which model actually
    # answered, including after a quota-driven fallback.
    model_used = getattr(client, "last_model_used", None)
    fallback_occurred = getattr(client, "last_fallback_occurred", False)

    try:
        diagnosis = parse_ai_response(raw)
    except Exception as exc:  # noqa: BLE001 - never let a bad response crash the app
        return DiagnosisResult(
            case_id=case.get("case_id", ""),
            ai_diagnosis=None,
            rule_findings=rule_findings,
            mock_mode=client.is_mock,
            error=f"The AI response could not be parsed as valid structured output: {exc}",
            raw_response=raw,
            model_used=model_used,
            fallback_occurred=fallback_occurred,
        )

    return DiagnosisResult(
        case_id=case.get("case_id", ""),
        ai_diagnosis=diagnosis,
        rule_findings=rule_findings,
        mock_mode=client.is_mock,
        raw_response=raw,
        model_used=model_used,
        fallback_occurred=fallback_occurred,
    )
