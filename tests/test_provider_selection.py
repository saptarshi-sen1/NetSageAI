"""
Environment-aware AI provider selection tests.

These verify backend/ai/client.py::get_ai_client()'s actual
environment-based selection logic directly - the real logic that runs
in production, completely unrelated to the test-only dependency
override in tests/conftest.py (which exists purely so *endpoint* tests
like test_api.py::test_diagnose_endpoint_mock_mode can assert
mock_mode=True regardless of the developer's real environment).

Supported providers: `gemini` (the real AI backend) and `mock`
(deterministic, offline - used for tests/local development with no API
key). There is no other real provider in this product.

Together, these two mechanisms give the test suite exactly the
environment-aware coverage described in the project's requirements:
  - "In mock/test configuration, expect mock_mode=True"      -> covered
    here by test_auto_detect_mock_when_no_keys_set, and by every
    endpoint test via the conftest.py override.
  - "In real Gemini configuration, expect mock_mode=False"    -> covered
    here by test_auto_detect_gemini_when_gemini_key_set and
    test_explicit_ai_provider_gemini.

None of these tests call .complete() on a real client, so none of them
make a live network request or require a real API key - they only
construct the client and assert on its type/config, which is enough to
prove the selection logic itself is correct.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import backend.ai.client as client_module
from backend.ai.client import (
    GeminiAIClient,
    MockAIClient,
    get_ai_client,
    reset_ai_client_singleton,
)


@pytest.fixture(autouse=True)
def isolated_client_singleton(monkeypatch):
    """Every test in this file needs a completely clean slate: no
    leftover cached singleton from a previous test, and no leftover
    provider env vars from the real shell/`.env` this suite happens to
    be running under. Without this, test order or the developer's real
    environment could leak between tests."""
    for var in ("AI_PROVIDER", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    reset_ai_client_singleton()
    yield
    reset_ai_client_singleton()


# --------------------------------------------------------------------------
# Mock configuration
# --------------------------------------------------------------------------
def test_auto_detect_mock_when_no_keys_set():
    """No provider keys at all -> MockAIClient, mock_mode is effectively
    True (MockAIClient.is_mock == True)."""
    client = get_ai_client()
    assert isinstance(client, MockAIClient)
    assert client.is_mock is True


def test_force_mock_true_always_returns_mock_even_with_real_key_present(monkeypatch):
    """The force_mock=True path (used by tests/conftest.py's dependency
    override) must win regardless of what's in the environment - this
    is the actual mechanism that makes endpoint tests reliable."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-should-be-ignored")
    client = get_ai_client(force_mock=True)
    assert isinstance(client, MockAIClient)


def test_explicit_ai_provider_mock(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("AI_PROVIDER", "mock")
    client = get_ai_client()
    assert isinstance(client, MockAIClient)


# --------------------------------------------------------------------------
# Real Gemini configuration
# --------------------------------------------------------------------------
def test_auto_detect_gemini_when_gemini_key_set(monkeypatch):
    """A real (or real-looking) GEMINI_API_KEY with no explicit
    AI_PROVIDER -> auto-detects GeminiAIClient. This is the exact
    configuration the project is meant to run under with a real key -
    verifying it here (safely, with a fake key and no .complete() call)
    is what proves 'real Gemini configuration' is still fully
    supported and not weakened by the mock-mode test fix."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-selection-test-only")
    client = get_ai_client()
    assert isinstance(client, GeminiAIClient)
    assert client.is_mock is False


def test_gemini_uses_default_model_chain_when_unconfigured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_FALLBACK_MODELS", raising=False)
    client = get_ai_client()
    assert isinstance(client, GeminiAIClient)
    assert client.model_chain == client_module.DEFAULT_GEMINI_MODEL_CHAIN


def test_gemini_respects_configured_model_chain(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-custom-primary")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "gemini-custom-fallback")
    client = get_ai_client()
    assert isinstance(client, GeminiAIClient)
    assert client.model_chain == ["gemini-custom-primary", "gemini-custom-fallback"]


def test_explicit_ai_provider_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    client = get_ai_client()
    assert isinstance(client, GeminiAIClient)


# --------------------------------------------------------------------------
# Fallback safety: broken explicit provider config never crashes the app
# --------------------------------------------------------------------------
def test_explicit_gemini_provider_without_key_falls_back_to_mock(monkeypatch):
    """AI_PROVIDER=gemini but no GEMINI_API_KEY -> the app must not
    crash; it degrades to MockAIClient (see get_ai_client's docstring)."""
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = get_ai_client()
    assert isinstance(client, MockAIClient)


def test_unknown_explicit_provider_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "not-a-real-provider")
    client = get_ai_client()
    assert isinstance(client, MockAIClient)


# --------------------------------------------------------------------------
# Singleton caching behavior (documents WHY conftest.py's override exists)
# --------------------------------------------------------------------------
def test_singleton_caches_across_calls_within_same_environment(monkeypatch):
    """This is the exact behavior that made the original bug report
    real: once get_ai_client() picks a provider, it's cached for
    subsequent calls without re-reading the environment. This is
    correct/intended production behavior (don't reconstruct an SDK
    client on every request) - it's precisely why endpoint tests need
    the dependency-override mechanism in conftest.py rather than
    relying on get_ai_client() alone."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    first = get_ai_client()
    # Even if the env var changed after the first call, the cached
    # singleton is returned - proving why endpoint-level tests can't
    # just rely on env manipulation after the app has already started.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    second = get_ai_client()
    assert first is second
    assert isinstance(second, GeminiAIClient)
