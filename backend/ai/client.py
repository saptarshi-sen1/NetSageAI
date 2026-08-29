"""
NetSage AI - AI Client Abstraction Layer

This module is the ONLY place that talks to an LLM provider. Everything
above it (backend/ai/diagnosis.py, the API routes) works against the
AIClient interface, so swapping providers - or changing which models a
provider falls back across - never touches the rest of the app.

Two implementations:
  - GeminiAIClient: calls the real Google Gemini API, with automatic
    fallback across an ordered list of models when one is rate-limited
    or its quota is exhausted (HTTP 429 / RESOURCE_EXHAUSTED), when a
    model is unavailable (404), or when it returns a transient server
    error (5xx).
  - MockAIClient: returns deterministic canned responses, so the whole
    application works with zero API key configured.

get_ai_client() picks whichever is appropriate based on environment
variables (AI_PROVIDER, GEMINI_API_KEY) and is what the rest of the
backend should import.
"""
from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from backend.ai.mock_data import SCRIPTED_EDITED, SCRIPTED_REJECTED

DEFAULT_GEMINI_MODEL_CHAIN = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-001",
    "gemini-2.5-pro",
]

SAME_MODEL_RETRY_ATTEMPTS = 2
SAME_MODEL_RETRY_BASE_DELAY_SECONDS = 0.6


class AIClientError(Exception):
    """Raised when every configured model/provider attempt fails outright
    (auth error, or every model in the fallback chain was exhausted).
    Distinct from a parse failure, which is handled separately in
    diagnosis.py so a bad response never crashes the app."""


class AIClient(ABC):
    """Minimal interface every AI backend must implement."""

    last_model_used: Optional[str] = None
    last_fallback_occurred: bool = False

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, case: Optional[dict] = None) -> str:
        """Return the raw text response for a single-turn completion.

        `case` is an OPTIONAL convenience reference to the full case dict,
        used only by MockAIClient so it can generate a tailored offline
        response without re-parsing the prompt text. Every real provider
        client ignores it entirely - the model only ever sees what's in
        system_prompt/user_prompt, exactly like the live API.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        raise NotImplementedError


class GeminiAIClient(AIClient):
    """Real Google Gemini API client with automatic model fallback.

    If the primary model's quota is exhausted (429 / RESOURCE_EXHAUSTED),
    is temporarily unavailable (5xx after retrying), or doesn't exist on
    this key/tier (404), the client automatically retries the SAME
    request against the next model in `model_chain` instead of failing
    the diagnosis outright.
    """

    def __init__(self, api_key: str, model_chain: Optional[List[str]] = None):
        try:
            from google import genai as google_genai
            from google.genai import errors as genai_errors
        except ImportError as exc:  # pragma: no cover
            raise AIClientError(
                "The 'google-genai' package is required for Gemini mode. "
                "Install it with: pip install google-genai"
            ) from exc

        self._genai = google_genai
        self._errors = genai_errors
        self._client = google_genai.Client(api_key=api_key)
        self.model_chain = model_chain or self._resolve_model_chain()

        if not self.model_chain:
            raise AIClientError(
                "No Gemini models configured. Set GEMINI_MODEL and/or "
                "GEMINI_FALLBACK_MODELS in .env."
            )

    @staticmethod
    def _resolve_model_chain() -> List[str]:
        """Build the ordered model list from environment variables, with
        a documented, sensible built-in default. GEMINI_MODEL (if set)
        is always tried first; GEMINI_FALLBACK_MODELS (comma-separated)
        is appended after it; duplicates are dropped while preserving
        order."""
        primary = os.getenv("GEMINI_MODEL", "").strip()
        fallbacks_raw = os.getenv("GEMINI_FALLBACK_MODELS", "").strip()
        fallbacks = [m.strip() for m in fallbacks_raw.split(",") if m.strip()]

        if primary or fallbacks:
            chain = ([primary] if primary else []) + fallbacks
        else:
            chain = list(DEFAULT_GEMINI_MODEL_CHAIN)

        seen = set()
        deduped = []
        for model in chain:
            if model not in seen:
                seen.add(model)
                deduped.append(model)
        return deduped

    @property
    def is_mock(self) -> bool:
        return False

    def complete(self, system_prompt: str, user_prompt: str, case: Optional[dict] = None) -> str:
        from google.genai import types as genai_types

        from backend.ai.schemas import AIDiagnosis

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            # Reasoning-capable models (the gemini-2.5 family) can spend
            # their entire token budget on internal "thinking" before
            # ever emitting the JSON answer, leaving response.text empty
            # or truncated - this was the root cause of a real
            # "Expecting value: line 1 column 1 (char 0)" parse failure
            # seen with a live API key (raw model output was empty/
            # prose-only, not valid JSON). 4000 tokens leaves headroom
            # for both a bounded thinking pass and the full structured
            # diagnosis object.
            max_output_tokens=4000,
            thinking_config=genai_types.ThinkingConfig(
                # Caps how many tokens the model may spend "thinking"
                # before it must start producing the actual (JSON)
                # answer, so thinking can no longer consume the whole
                # max_output_tokens budget and starve the real response.
                thinking_budget=1024,
                include_thoughts=False,
            ),
            # Native structured output: instructs Gemini's API boundary
            # itself to constrain generation to valid JSON matching
            # AIDiagnosis's schema, rather than relying solely on prompt
            # instructions ("respond with ONLY a JSON object") that a
            # model can silently ignore. This is the preferred fix per
            # docs/responsible_ai.md's evidence-grounding requirements -
            # it makes malformed/prose-only output structurally far less
            # likely, while backend/ai/diagnosis.py's parse_ai_response()
            # and its try/except in diagnose() remain as defense-in-depth
            # for any model/SDK edge case this doesn't cover.
            response_mime_type="application/json",
            response_schema=AIDiagnosis,
        )

        attempt_errors: List[str] = []

        for index, model in enumerate(self.model_chain):
            is_fallback_attempt = index > 0
            try:
                text = self._call_model_with_retry(model, user_prompt, config)
                self.last_model_used = model
                self.last_fallback_occurred = is_fallback_attempt
                return text
            except _SkipToNextModel as exc:
                attempt_errors.append(f"{model}: {exc}")
                continue
            except _FatalAIError as exc:
                raise AIClientError(f"Gemini API call failed ({model}): {exc}") from exc

        raise AIClientError(
            "All configured Gemini models were unavailable or exhausted. "
            "Tried: " + " | ".join(attempt_errors)
        )

    def _call_model_with_retry(self, model: str, user_prompt: str, config) -> str:
        last_exc: Optional[Exception] = None

        for attempt in range(1, SAME_MODEL_RETRY_ATTEMPTS + 1):
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=config,
                )
                text = getattr(response, "text", None)
                if not text:
                    raise _SkipToNextModel("empty response body")
                return text
            except self._errors.APIError as exc:
                code = getattr(exc, "code", None)
                status = (getattr(exc, "status", None) or "").upper()

                if code in (401, 403):
                    raise _FatalAIError(f"authentication/permission error ({code} {status}): {exc}")

                if code == 429 or status == "RESOURCE_EXHAUSTED":
                    raise _SkipToNextModel(f"quota exhausted ({code} {status})")

                if code == 404:
                    raise _SkipToNextModel(f"model not available on this key/tier ({code})")

                if code and code >= 500:
                    last_exc = exc
                    if attempt < SAME_MODEL_RETRY_ATTEMPTS:
                        time.sleep(SAME_MODEL_RETRY_BASE_DELAY_SECONDS * attempt)
                        continue
                    raise _SkipToNextModel(f"server error after retrying ({code}): {exc}")

                raise _SkipToNextModel(f"unexpected API error ({code} {status}): {exc}")
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < SAME_MODEL_RETRY_ATTEMPTS:
                    time.sleep(SAME_MODEL_RETRY_BASE_DELAY_SECONDS * attempt)
                    continue
                raise _SkipToNextModel(f"call failed after retrying: {exc}")

        raise _SkipToNextModel(f"exhausted retries: {last_exc}")


class _SkipToNextModel(Exception):
    """Internal signal: this model failed in a way that justifies
    falling back to the next model in the chain."""


class _FatalAIError(Exception):
    """Internal signal: this failure will affect every model equally
    (e.g. bad API key), so the whole chain should be abandoned."""


class MockAIClient(AIClient):
    """Deterministic, offline stand-in for the real API. Used automatically
    whenever no provider API key is set, so the whole app works with zero
    configuration. Same case_id always produces the same mock diagnosis.
    """

    _DIFFICULTY_CONFIDENCE = {
        "Easy": 0.9,
        "Medium": 0.72,
        "Hard": 0.48,
    }

    @property
    def is_mock(self) -> bool:
        return True

    def complete(self, system_prompt: str, user_prompt: str, case: Optional[dict] = None) -> str:
        resolved_case = case or self._extract_case_from_prompt(user_prompt)
        diagnosis = self.generate_mock_diagnosis(resolved_case)
        self.last_model_used = "mock"
        self.last_fallback_occurred = False
        return json.dumps(diagnosis)

    @staticmethod
    def _extract_case_from_prompt(user_prompt: str) -> dict:
        marker = "CASE_JSON_START"
        end_marker = "CASE_JSON_END"
        try:
            start = user_prompt.index(marker) + len(marker)
            end = user_prompt.index(end_marker)
            return json.loads(user_prompt[start:end].strip())
        except (ValueError, json.JSONDecodeError):
            return {}

    @classmethod
    def generate_mock_diagnosis(cls, case: dict) -> dict:
        case_id = case.get("case_id", "")

        if case_id in SCRIPTED_REJECTED:
            return dict(SCRIPTED_REJECTED[case_id])
        if case_id in SCRIPTED_EDITED:
            return dict(SCRIPTED_EDITED[case_id])

        return cls._generate_grounded_diagnosis(case)

    @classmethod
    def _generate_grounded_diagnosis(cls, case: dict) -> dict:
        difficulty = case.get("difficulty", "Medium")
        confidence = cls._DIFFICULTY_CONFIDENCE.get(difficulty, 0.7)
        confidence_label = "High" if confidence >= 0.8 else ("Medium" if confidence >= 0.5 else "Low")

        expected_evidence = case.get("expected_evidence", "") or ""
        evidence_list = [
            e.strip().rstrip(".") + "."
            for e in _split_sentences(expected_evidence)
            if e.strip()
        ] or ["See supplied show-command output for this case."]

        fix_text = case.get("expected_fix", "") or "Further investigation required before proposing a fix."
        fix_steps = [s.strip() for s in fix_text.split(";") if s.strip()] or [fix_text]

        verification_text = case.get("verification_command", "") or ""
        verification_steps = [s.strip() for s in verification_text.split(";") if s.strip()] or (
            [verification_text] if verification_text else []
        )

        root_cause = case.get("expected_fault", "Unable to determine root cause from the supplied evidence.")

        return {
            "root_cause": root_cause,
            "confidence": confidence,
            "confidence_label": confidence_label,
            "osi_layer": case.get("osi_layer", "Unknown"),
            "concept": case.get("concept", "Unknown"),
            "evidence": evidence_list,
            "reasoning_summary": (
                f"The supplied evidence ({expected_evidence.rstrip('.')}) is "
                f"consistent with: {root_cause}"
                if expected_evidence
                else root_cause
            ),
            "next_command": case.get("expected_next_command", ""),
            "fix_steps": fix_steps,
            "verification_steps": verification_steps,
            "human_review_required": True,
        }


def _split_sentences(text: str) -> list[str]:
    parts: list[str] = []
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        sub_parts = [p.strip() for p in chunk.split(". ") if p.strip()]
        parts.extend(sub_parts if sub_parts else [chunk])
    return parts


_client_singleton: Optional[AIClient] = None


def _build_client_for_provider(provider: str) -> AIClient:
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise AIClientError("AI_PROVIDER=gemini but GEMINI_API_KEY is not set.")
        return GeminiAIClient(api_key=api_key)

    if provider == "mock":
        return MockAIClient()

    raise AIClientError(f"Unknown AI_PROVIDER '{provider}'. Use 'gemini' or 'mock'.")


def get_ai_client(force_mock: bool = False) -> AIClient:
    """Return the appropriate AI client for the current environment.
    Cached as a module-level singleton.

    Selection order:
      1. force_mock=True (used by tests) -> always MockAIClient.
      2. AI_PROVIDER env var, if set -> that provider explicitly.
      3. Otherwise, auto-detect: GEMINI_API_KEY -> Gemini, else MockAIClient.
    If the selected real provider fails to initialize (missing package,
    missing key), the app falls back to MockAIClient rather than
    becoming completely unusable.
    """
    global _client_singleton

    if force_mock:
        return MockAIClient()

    if _client_singleton is not None:
        return _client_singleton

    explicit_provider = os.getenv("AI_PROVIDER", "").strip().lower()

    if explicit_provider:
        try:
            _client_singleton = _build_client_for_provider(explicit_provider)
        except AIClientError:
            _client_singleton = MockAIClient()
        return _client_singleton

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    if gemini_key:
        try:
            _client_singleton = GeminiAIClient(api_key=gemini_key)
        except AIClientError:
            _client_singleton = MockAIClient()
    else:
        _client_singleton = MockAIClient()

    return _client_singleton


def reset_ai_client_singleton() -> None:
    """Test helper: clears the cached client so a test can change env
    vars and get a freshly-configured client on the next get_ai_client()
    call."""
    global _client_singleton
    _client_singleton = None
