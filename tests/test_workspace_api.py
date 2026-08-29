"""
API-level tests for /api/attempts/* and /api/workspace/* endpoints.
Uses isolated temp CSVs for both cases.csv and attempts.csv so these
tests never touch real seed data. Reuses the shared `client` fixture
from conftest.py (which forces AI-diagnosis mock mode) even though
these particular endpoints don't call the AI - kept for consistency
with the rest of the API test suite.
"""
import csv
import os
import sys

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND_DIR = os.path.join(_PROJECT_ROOT, "backend")
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, _BACKEND_DIR)

from backend.services import attempt_service, case_service


@pytest.fixture(autouse=True)
def isolated_cases_csv(monkeypatch, tmp_path):
    temp_csv = tmp_path / "cases.csv"
    with open(temp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=case_service.FIELDS)
        writer.writeheader()
        for case_id, concept in [("WS-001", "VLAN"), ("WS-002", "VLAN"), ("WS-003", "DHCP")]:
            writer.writerow(
                {
                    "case_id": case_id,
                    "title": f"Workspace test case {case_id}",
                    "symptom": "symptom",
                    "topology_note": "topology",
                    "show_outputs": "show ip route\noutput",
                    "expected_fault": "fault",
                    "osi_layer": "Layer 3",
                    "concept": concept,
                    "severity": "Medium",
                    "expected_evidence": "evidence",
                    "expected_next_command": "show ip route",
                    "expected_fix": "fix",
                    "verification_command": "ping test",
                    "difficulty": "Easy",
                    "status": "active",
                    "source": "seed",
                    "created_at": "2026-06-01T00:00:00Z",
                    "updated_at": "2026-06-01T00:00:00Z",
                    "created_by": "Course Dataset",
                }
            )
    monkeypatch.setattr(case_service, "CASES_CSV_PATH", str(temp_csv))
    case_service._load_all_cases_cached.cache_clear()
    yield
    case_service._load_all_cases_cached.cache_clear()


@pytest.fixture(autouse=True)
def isolated_attempts_csv(monkeypatch, tmp_path):
    temp_csv = tmp_path / "attempts.csv"
    monkeypatch.setattr(attempt_service, "ATTEMPTS_CSV_PATH", str(temp_csv))
    yield


@pytest.fixture(autouse=True)
def isolated_reviews_csv(monkeypatch, tmp_path):
    from backend.services import review_service

    temp_csv = tmp_path / "reviews.csv"
    monkeypatch.setattr(review_service, "REVIEWS_CSV_PATH", str(temp_csv))
    yield


# --------------------------------------------------------------------------
# Start / complete
# --------------------------------------------------------------------------
def test_start_attempt(client):
    r = client.post("/api/attempts/start", json={"case_id": "WS-001", "student_name": "Alice"})
    assert r.status_code == 200
    attempt = r.json()["attempt"]
    assert attempt["case_id"] == "WS-001"
    assert attempt["status"] == "IN_PROGRESS"


def test_start_attempt_default_student_name(client):
    r = client.post("/api/attempts/start", json={"case_id": "WS-001"})
    assert r.status_code == 200
    assert r.json()["attempt"]["student_name"] == "Anonymous"


def test_start_attempt_missing_case_id_rejected(client):
    r = client.post("/api/attempts/start", json={"student_name": "Alice"})
    assert r.status_code == 422


def test_complete_attempt(client):
    start_resp = client.post("/api/attempts/start", json={"case_id": "WS-001", "student_name": "Alice"})
    attempt_id = start_resp.json()["attempt"]["attempt_id"]

    r = client.post(f"/api/attempts/{attempt_id}/complete", json={})
    assert r.status_code == 200
    assert r.json()["attempt"]["status"] == "COMPLETED"


def test_complete_attempt_with_practice_fields(client):
    start_resp = client.post("/api/attempts/start", json={"case_id": "WS-001", "student_name": "Alice"})
    attempt_id = start_resp.json()["attempt"]["attempt_id"]

    r = client.post(
        f"/api/attempts/{attempt_id}/complete",
        json={
            "student_root_cause": "My hypothesis",
            "student_osi_layer": "Layer 2",
            "ai_root_cause": "AI's hypothesis",
            "matches_expected_concept": True,
        },
    )
    assert r.status_code == 200
    body = r.json()["attempt"]
    assert body["student_root_cause"] == "My hypothesis"
    assert body["ai_root_cause"] == "AI's hypothesis"


def test_complete_nonexistent_attempt_404(client):
    r = client.post("/api/attempts/ATT-9999/complete", json={})
    assert r.status_code == 404


# --------------------------------------------------------------------------
# List attempts
# --------------------------------------------------------------------------
def test_list_attempts_for_student(client):
    client.post("/api/attempts/start", json={"case_id": "WS-001", "student_name": "Alice"})
    client.post("/api/attempts/start", json={"case_id": "WS-002", "student_name": "Bob"})

    r = client.get("/api/attempts?student_name=Alice")
    assert r.status_code == 200
    attempts = r.json()["attempts"]
    assert len(attempts) == 1
    assert attempts[0]["case_id"] == "WS-001"


def test_list_attempts_missing_student_name_422(client):
    r = client.get("/api/attempts")
    assert r.status_code == 422


# --------------------------------------------------------------------------
# Workspace summary
# --------------------------------------------------------------------------
def test_workspace_summary_no_attempts(client):
    r = client.get("/api/workspace/summary?student_name=NewStudent")
    assert r.status_code == 200
    data = r.json()
    assert data["total_available_cases"] == 3
    assert data["attempted_count"] == 0
    assert data["completed_count"] == 0
    assert "safety_notice" in data


def test_workspace_summary_reflects_progress(client):
    start_resp = client.post("/api/attempts/start", json={"case_id": "WS-001", "student_name": "Alice"})
    attempt_id = start_resp.json()["attempt"]["attempt_id"]
    client.post("/api/attempts/start", json={"case_id": "WS-002", "student_name": "Alice"})
    client.post(f"/api/attempts/{attempt_id}/complete", json={})

    r = client.get("/api/workspace/summary?student_name=Alice")
    data = r.json()
    assert data["attempted_count"] == 2
    assert data["completed_count"] == 1
    assert data["in_progress_count"] == 1


def test_workspace_summary_practice_by_concept(client):
    start_resp = client.post("/api/attempts/start", json={"case_id": "WS-001", "student_name": "Alice"})
    client.post(f"/api/attempts/{start_resp.json()['attempt']['attempt_id']}/complete", json={})

    r = client.get("/api/workspace/summary?student_name=Alice")
    concept_data = r.json()["practice_by_concept"]
    assert concept_data["VLAN"]["total"] == 2
    assert concept_data["VLAN"]["completed"] == 1
    assert concept_data["DHCP"]["total"] == 1
    assert concept_data["DHCP"]["completed"] == 0


def test_workspace_summary_missing_student_name_422(client):
    r = client.get("/api/workspace/summary")
    assert r.status_code == 422


def test_workspace_summary_isolates_students(client):
    start_resp = client.post("/api/attempts/start", json={"case_id": "WS-001", "student_name": "Alice"})
    client.post(f"/api/attempts/{start_resp.json()['attempt']['attempt_id']}/complete", json={})
    client.post("/api/attempts/start", json={"case_id": "WS-001", "student_name": "Bob"})

    alice_summary = client.get("/api/workspace/summary?student_name=Alice").json()
    bob_summary = client.get("/api/workspace/summary?student_name=Bob").json()
    assert alice_summary["completed_count"] == 1
    assert bob_summary["completed_count"] == 0


# --------------------------------------------------------------------------
# Case status map
# --------------------------------------------------------------------------
def test_case_status_map(client):
    start_resp = client.post("/api/attempts/start", json={"case_id": "WS-001", "student_name": "Alice"})
    client.post(f"/api/attempts/{start_resp.json()['attempt']['attempt_id']}/complete", json={})
    client.post("/api/attempts/start", json={"case_id": "WS-002", "student_name": "Alice"})

    r = client.get("/api/workspace/case-status?student_name=Alice")
    assert r.status_code == 200
    status_map = r.json()["case_status"]
    assert status_map["WS-001"] == "completed"
    assert status_map["WS-002"] == "in_progress"
    assert status_map["WS-003"] == "not_started"


def test_case_status_map_missing_student_name_422(client):
    r = client.get("/api/workspace/case-status")
    assert r.status_code == 422
