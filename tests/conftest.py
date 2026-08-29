"""
Shared pytest fixtures for the whole test suite.

## Why this file exists

backend/ai/client.py::get_ai_client() caches its result in a
module-level singleton and reads GEMINI_API_KEY from the environment
exactly once per process. That's the right
behavior in production (don't re-parse env vars and re-construct an
SDK client on every request) - but it means that if a developer runs
`pytest` in a shell that has a REAL GEMINI_API_KEY exported (or a
project-root .env with one in it), the very first call to
get_ai_client() from ANY test would permanently select a real
GeminiAIClient for the rest of that pytest process, regardless of what
any individual test wants to verify. Endpoint tests that assert
`mock_mode is True` would then fail - not because anything is broken,
but because the test suite wasn't controlling for its own environment.

Worse: a real GeminiAIClient means POST /api/diagnose would attempt a
live network call to generativelanguage.googleapis.com on every test
run - spending real API quota/cost just from running `pytest`, and
making the suite's pass/fail depend on network reachability.

## The fix

backend/api/diagnosis.py's /api/diagnose route resolves its AIClient
through a FastAPI dependency (`_resolve_ai_client`), specifically so
tests can override *only that one dependency* via
`app.dependency_overrides`, without touching get_ai_client()'s real
env-based selection logic at all:

  - `client` (mock-mode, used by most tests): installs an override that
    always returns a fresh MockAIClient. These tests assert
    mock_mode=True and never touch the network, regardless of the
    developer's real .env.
  - `real_provider_client` (opt-in, used only by
    tests/test_provider_selection.py): does NOT install any override,
    so it exercises get_ai_client()'s actual environment-based
    selection - but those tests construct clients directly and assert
    on *type*, never actually calling .complete(), so they still never
    make a live network call either.

Every other existing fixture (isolated_cases_csv, isolated_reviews_csv,
etc.) is unaffected - this file only centralizes what test_api.py and
test_case_api.py were already each defining as `client()`.
"""
from __future__ import annotations

import os
import sys

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND_DIR = os.path.join(_PROJECT_ROOT, "backend")
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


@pytest.fixture()
def client():
    """The standard TestClient used by nearly every API test. Always
    forces the AI diagnosis pipeline into mock mode via a FastAPI
    dependency override - see module docstring for why this matters.
    Tests using this fixture can reliably assert `mock_mode is True`
    no matter what's in the real environment's .env, and never make a
    live network call to any AI provider."""
    from fastapi.testclient import TestClient

    from backend.ai.client import MockAIClient
    from backend.api.diagnosis import _resolve_ai_client
    from main import app

    app.dependency_overrides[_resolve_ai_client] = lambda: MockAIClient()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(_resolve_ai_client, None)
