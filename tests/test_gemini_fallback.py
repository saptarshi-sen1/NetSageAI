"""
Tests for GeminiAIClient's automatic model-fallback behavior. These
stub out the google.genai SDK entirely (no real network calls, no API
key needed) so the fallback LOGIC itself is what's under test: given a
sequence of per-model outcomes, does the client fall back correctly,
skip correctly, and fail closed correctly.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google.genai import errors as genai_errors

from backend.ai.client import (
    AIClientError,
    DEFAULT_GEMINI_MODEL_CHAIN,
    GeminiAIClient,
)


def _api_error(code: int, status: str, message: str = "boom") -> genai_errors.APIError:
    """Build a real google.genai APIError with the given code/status, the
    same way the SDK itself constructs one from a response body."""
    response_json = {"error": {"code": code, "status": status, "message": message}}
    return genai_errors.APIError(code, response_json)


class FakeModelsAPI:
    """Stand-in for client.models - returns a scripted outcome per model
    name, in call order, from `script`. Each scripted outcome is either
    a string (successful response text) or an Exception instance/class
    to raise."""

    def __init__(self, script: dict):
        self.script = script
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        outcome = self.script.get(model)
        if outcome is None:
            raise AssertionError(f"No scripted outcome for model {model}")
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, type) and issubclass(outcome, Exception):
            raise outcome()

        class _Resp:
            text = outcome

        return _Resp()


def make_client(script: dict, model_chain=None) -> GeminiAIClient:
    """Construct a GeminiAIClient without touching the network: swap in
    a FakeModelsAPI after construction, bypassing real credential setup."""
    client = GeminiAIClient.__new__(GeminiAIClient)
    client.model_chain = model_chain or ["model-a", "model-b", "model-c"]
    client._errors = genai_errors
    client.last_model_used = None
    client.last_fallback_occurred = False

    class _FakeGenaiClient:
        def __init__(self):
            self.models = FakeModelsAPI(script)

    client._client = _FakeGenaiClient()
    return client


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------
def test_primary_model_success_no_fallback():
    client = make_client({"model-a": '{"ok": true}'})
    result = client.complete("system", "user prompt")
    assert result == '{"ok": true}'
    assert client.last_model_used == "model-a"
    assert client.last_fallback_occurred is False
    assert client._client.models.calls == ["model-a"]


# --------------------------------------------------------------------------
# Quota exhaustion -> immediate fallback, no wasted retries on same model
# --------------------------------------------------------------------------
def test_quota_exhausted_falls_back_to_next_model():
    client = make_client(
        {
            "model-a": _api_error(429, "RESOURCE_EXHAUSTED"),
            "model-b": '{"ok": true}',
        }
    )
    result = client.complete("system", "user prompt")
    assert result == '{"ok": true}'
    assert client.last_model_used == "model-b"
    assert client.last_fallback_occurred is True
    # Only ONE call to model-a - quota errors should not be retried on
    # the same model, since retrying won't refill the quota.
    assert client._client.models.calls == ["model-a", "model-b"]


def test_quota_exhausted_on_every_model_raises_clean_error():
    client = make_client(
        {
            "model-a": _api_error(429, "RESOURCE_EXHAUSTED"),
            "model-b": _api_error(429, "RESOURCE_EXHAUSTED"),
            "model-c": _api_error(429, "RESOURCE_EXHAUSTED"),
        }
    )
    with pytest.raises(AIClientError) as exc_info:
        client.complete("system", "user prompt")
    assert "model-a" in str(exc_info.value)
    assert "model-b" in str(exc_info.value)
    assert "model-c" in str(exc_info.value)


# --------------------------------------------------------------------------
# Model not available on this key/tier (404) -> fallback
# --------------------------------------------------------------------------
def test_model_not_found_falls_back():
    client = make_client(
        {
            "model-a": _api_error(404, "NOT_FOUND"),
            "model-b": '{"ok": true}',
        }
    )
    result = client.complete("system", "user prompt")
    assert result == '{"ok": true}'
    assert client.last_model_used == "model-b"


# --------------------------------------------------------------------------
# Transient server error -> retried on same model, THEN falls back
# --------------------------------------------------------------------------
def test_server_error_retries_same_model_before_falling_back(monkeypatch):
    import backend.ai.client as client_module

    monkeypatch.setattr(client_module, "SAME_MODEL_RETRY_BASE_DELAY_SECONDS", 0)

    script = {
        "model-a": _api_error(503, "UNAVAILABLE"),
        "model-b": '{"ok": true}',
    }
    client = make_client(script)

    result = client.complete("system", "user prompt")
    assert result == '{"ok": true}'
    # model-a should have been attempted SAME_MODEL_RETRY_ATTEMPTS times
    # before falling back to model-b.
    assert client._client.models.calls.count("model-a") == client_module.SAME_MODEL_RETRY_ATTEMPTS
    assert client._client.models.calls[-1] == "model-b"


# --------------------------------------------------------------------------
# Auth failure -> fails fast, does NOT waste time trying every model
# --------------------------------------------------------------------------
def test_auth_failure_does_not_try_remaining_models():
    client = make_client(
        {
            "model-a": _api_error(401, "UNAUTHENTICATED"),
        }
    )
    with pytest.raises(AIClientError) as exc_info:
        client.complete("system", "user prompt")
    assert "authentication" in str(exc_info.value).lower()
    # Only model-a should ever have been attempted.
    assert client._client.models.calls == ["model-a"]


def test_permission_denied_does_not_try_remaining_models():
    client = make_client({"model-a": _api_error(403, "PERMISSION_DENIED")})
    with pytest.raises(AIClientError):
        client.complete("system", "user prompt")
    assert client._client.models.calls == ["model-a"]


# --------------------------------------------------------------------------
# Empty response body is treated as a failure, not a silent empty diagnosis
# --------------------------------------------------------------------------
def test_empty_response_falls_back():
    client = make_client({"model-a": "", "model-b": '{"ok": true}'})
    result = client.complete("system", "user prompt")
    assert result == '{"ok": true}'
    assert client.last_model_used == "model-b"


# --------------------------------------------------------------------------
# Model chain resolution from environment variables
# --------------------------------------------------------------------------
def test_resolve_model_chain_uses_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_FALLBACK_MODELS", raising=False)
    assert GeminiAIClient._resolve_model_chain() == DEFAULT_GEMINI_MODEL_CHAIN


def test_resolve_model_chain_respects_env_vars(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "custom-primary")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "custom-b, custom-c")
    chain = GeminiAIClient._resolve_model_chain()
    assert chain == ["custom-primary", "custom-b", "custom-c"]


def test_resolve_model_chain_deduplicates(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "same-model")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "same-model, other-model")
    chain = GeminiAIClient._resolve_model_chain()
    assert chain == ["same-model", "other-model"]


# --------------------------------------------------------------------------
# Structured output / thinking-budget configuration
#
# Regression coverage for a real production failure: a live Gemini call
# returned "Expecting value: line 1 column 1 (char 0)" from
# json.loads(), traced to the model (gemini-2.5-flash, a reasoning
# model) returning prose or empty text instead of the required JSON
# object - most likely because its thinking budget consumed the whole
# max_output_tokens allowance before any answer text was emitted. The
# fix constrains generation with response_mime_type/response_schema
# (native structured output) and caps thinking_budget so there's always
# room left for the actual JSON answer. These tests verify the config
# GeminiAIClient actually sends captures that fix; the graceful
# fallback behavior for any response that's STILL malformed is covered
# separately in tests/test_api.py and tests/test_case_api.py's
# malformed-JSON tests, and reproduced directly by
# test_prose_only_response_still_handled_gracefully below.
# --------------------------------------------------------------------------
class ConfigCapturingModelsAPI:
    """Like FakeModelsAPI, but records the GenerateContentConfig object
    passed on each call so tests can assert on its fields directly."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.captured_configs = []

    def generate_content(self, model, contents, config):
        self.captured_configs.append(config)

        class _Resp:
            text = self.response_text

        return _Resp()


def _make_config_capturing_client(response_text: str) -> tuple:
    client = GeminiAIClient.__new__(GeminiAIClient)
    client.model_chain = ["gemini-2.5-flash"]
    client._errors = genai_errors
    client.last_model_used = None
    client.last_fallback_occurred = False

    models_api = ConfigCapturingModelsAPI(response_text)

    class _FakeGenaiClient:
        def __init__(self):
            self.models = models_api

    client._client = _FakeGenaiClient()
    return client, models_api


def test_complete_requests_native_json_structured_output():
    """The API call must ask Gemini for application/json output
    constrained to the AIDiagnosis schema, not rely on prompt
    instructions alone - this is the primary fix for prose-only
    responses breaking the parser."""
    from backend.ai.schemas import AIDiagnosis

    client, models_api = _make_config_capturing_client('{"root_cause": "x"}')
    client.complete("system prompt", "user prompt")

    assert len(models_api.captured_configs) == 1
    config = models_api.captured_configs[0]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is AIDiagnosis


def test_complete_sets_bounded_thinking_budget():
    """thinking_budget must be explicitly capped (not left at the
    model's AUTOMATIC default of -1), so a reasoning model can't spend
    its entire output allowance thinking and never emit the answer."""
    client, models_api = _make_config_capturing_client('{"root_cause": "x"}')
    client.complete("system prompt", "user prompt")

    config = models_api.captured_configs[0]
    assert config.thinking_config is not None
    assert config.thinking_config.thinking_budget is not None
    assert config.thinking_config.thinking_budget > 0
    # AUTOMATIC (-1) would defeat the whole point of capping it.
    assert config.thinking_config.thinking_budget != -1


def test_complete_max_output_tokens_leaves_room_beyond_thinking_budget():
    """max_output_tokens must comfortably exceed thinking_budget, so
    there's guaranteed room left for the actual JSON answer after
    thinking - otherwise capping thinking_budget alone wouldn't help."""
    client, models_api = _make_config_capturing_client('{"root_cause": "x"}')
    client.complete("system prompt", "user prompt")

    config = models_api.captured_configs[0]
    assert config.max_output_tokens > config.thinking_config.thinking_budget


def test_prose_only_response_still_handled_gracefully():
    """Even with structured output requested, defense-in-depth parsing
    must still degrade gracefully if a response is somehow still not
    valid JSON (the exact failure mode originally reported: prose with
    no JSON object at all, producing json.loads' 'char 0' error)."""
    from backend.ai.diagnosis import diagnose
    from backend.services.case_service import get_case

    client, _ = _make_config_capturing_client(
        "I need more information to analyze this case properly."
    )
    case = get_case("VLAN-001")
    result = diagnose(case, ai_client=client)

    assert result.ai_diagnosis is None
    assert result.error is not None
    assert "could not be parsed" in result.error


def test_empty_text_still_triggers_fallback_not_parser():
    """An empty response.text (e.g. the model emitted only a 'thought'
    part and no answer, per the google-genai SDK's _get_text()
    behavior) must be caught before reaching the JSON parser and
    treated as groundsfor model fallback, exactly like before this
    fix - this is the existing empty-response guard, still functioning
    with the new config fields in place."""
    client, models_api = _make_config_capturing_client("")
    with pytest.raises(AIClientError) as exc_info:
        client.complete("system prompt", "user prompt")
    assert "empty response body" in str(exc_info.value) or "unavailable or exhausted" in str(
        exc_info.value
    )
