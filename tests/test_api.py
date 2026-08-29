"""
API-level tests. Uses FastAPI's TestClient, so no server needs to be
running. A temporary reviews CSV is used so these tests never disturb
the real data/reviews.csv seed data.
"""
import os
import sys

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND_DIR = os.path.join(_PROJECT_ROOT, "backend")
sys.path.insert(0, _PROJECT_ROOT)
# main.py lives in backend/ and uses absolute `from backend.api import ...`
# imports, so backend/'s parent (the project root) must be on sys.path -
# that's already covered above. main.py itself is imported as a top-level
# module (`import main`), which requires backend/ itself on sys.path too.
sys.path.insert(0, _BACKEND_DIR)

from backend.ai.client import AIClient


@pytest.fixture(autouse=True)
def isolated_reviews_csv(monkeypatch, tmp_path):
    """Point the review service at a throwaway CSV for every test in
    this file, so tests never mutate the real seed data on disk."""
    from backend.services import review_service

    temp_csv = tmp_path / "reviews.csv"
    monkeypatch.setattr(review_service, "REVIEWS_CSV_PATH", str(temp_csv))
    yield


# NOTE: the `client` fixture used throughout this file is defined once,
# shared, in tests/conftest.py - it forces AI-diagnosis mock mode via a
# FastAPI dependency override so these tests behave identically whether
# or not a real GEMINI_API_KEY is set in the actual environment pytest
# runs in. See conftest.py's module docstring.


class BrokenJSONClient(AIClient):
    is_mock = False

    def complete(self, system_prompt, user_prompt, case=None):
        return "I'm sorry, here's some prose instead of JSON as requested."


class MissingFieldClient(AIClient):
    is_mock = False

    def complete(self, system_prompt, user_prompt, case=None):
        return '{"root_cause": "something"}'  # missing required fields


# --------------------------------------------------------------------------
# Basic endpoints
# --------------------------------------------------------------------------
def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "mock_mode" in r.json()


def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_cases(client):
    r = client.get("/api/cases")
    assert r.status_code == 200
    assert len(r.json()["cases"]) >= 30


def test_get_case_detail(client):
    r = client.get("/api/cases/VLAN-001")
    assert r.status_code == 200
    assert r.json()["case_id"] == "VLAN-001"


def test_get_case_detail_404(client):
    r = client.get("/api/cases/DOES-NOT-EXIST")
    assert r.status_code == 404


def test_check_endpoint(client):
    r = client.post("/api/check", json={"case_id": "IFACE-001"})
    assert r.status_code == 200
    findings = r.json()["findings"]
    assert any(f["rule"] == "interface_down" for f in findings)


def test_check_endpoint_404(client):
    r = client.post("/api/check", json={"case_id": "NOPE"})
    assert r.status_code == 404


# --------------------------------------------------------------------------
# Diagnosis endpoint - mock mode always available, always sets human review
# --------------------------------------------------------------------------
def test_diagnose_endpoint_mock_mode(client):
    r = client.post("/api/diagnose", json={"case_id": "VLAN-001"})
    assert r.status_code == 200
    data = r.json()
    assert data["mock_mode"] is True
    assert data["human_review_required"] is True
    assert data["ai_diagnosis"]["human_review_required"] is True
    assert data["error"] is None


def test_diagnose_endpoint_404(client):
    r = client.post("/api/diagnose", json={"case_id": "NOPE"})
    assert r.status_code == 404


# --------------------------------------------------------------------------
# Malformed AI JSON must never crash the app
# --------------------------------------------------------------------------
def test_malformed_ai_json_handled_gracefully():
    from backend.ai.diagnosis import diagnose
    from backend.services.case_service import get_case

    case = get_case("VLAN-001")
    result = diagnose(case, ai_client=BrokenJSONClient())
    assert result.ai_diagnosis is None
    assert result.error is not None


def test_ai_response_missing_required_fields_handled_gracefully():
    from backend.ai.diagnosis import diagnose
    from backend.services.case_service import get_case

    case = get_case("VLAN-001")
    result = diagnose(case, ai_client=MissingFieldClient())
    assert result.ai_diagnosis is None
    assert result.error is not None
    assert "could not be parsed" in result.error


# --------------------------------------------------------------------------
# Human review workflow: ACCEPT / EDIT / REJECT
# --------------------------------------------------------------------------
def test_review_accept(client):
    r = client.post(
        "/api/reviews",
        json={
            "case_id": "VLAN-001",
            "ai_root_cause": "Port is in the wrong VLAN",
            "ai_confidence": 0.9,
            "human_decision": "ACCEPTED",
            "reviewer": "Test Reviewer",
        },
    )
    assert r.status_code == 200
    assert r.json()["review"]["human_decision"] == "ACCEPTED"


def test_review_edit_records_correction(client):
    r = client.post(
        "/api/reviews",
        json={
            "case_id": "MASK-001",
            "ai_root_cause": "generic mask issue",
            "ai_confidence": 0.6,
            "human_decision": "EDITED",
            "human_root_cause": "Specific mask values identified",
            "correction_reason": "AI was too vague",
            "reviewer": "Test Reviewer",
        },
    )
    assert r.status_code == 200
    assert r.json()["review"]["human_decision"] == "EDITED"


def test_review_reject_requires_reason(client):
    r = client.post(
        "/api/reviews",
        json={
            "case_id": "STP-001",
            "ai_root_cause": "wrong diagnosis",
            "ai_confidence": 0.4,
            "human_decision": "REJECTED",
            "reviewer": "Test Reviewer",
            # correction_reason intentionally omitted
        },
    )
    assert r.status_code == 422


def test_review_reject_with_reason_succeeds(client):
    r = client.post(
        "/api/reviews",
        json={
            "case_id": "STP-001",
            "ai_root_cause": "wrong diagnosis",
            "ai_confidence": 0.4,
            "human_decision": "REJECTED",
            "correction_reason": "Evidence shows this is expected STP behavior, not a fault",
            "reviewer": "Test Reviewer",
        },
    )
    assert r.status_code == 200
    assert r.json()["review"]["human_decision"] == "REJECTED"


def test_dashboard_reflects_new_reviews(client):
    client.post(
        "/api/reviews",
        json={
            "case_id": "VLAN-001",
            "ai_root_cause": "x",
            "ai_confidence": 0.9,
            "human_decision": "ACCEPTED",
            "reviewer": "Test Reviewer",
        },
    )
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert data["reviewed"] >= 1
    assert data["decision_counts"]["ACCEPTED"] >= 1
    assert "safety_notice" in data
