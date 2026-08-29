"""
API-level tests for /api/practice/*. Uses isolated temp CSVs for
cases.csv, attempts.csv, and reviews.csv, and the shared `client`
fixture from conftest.py (forces AI-diagnosis mock mode via a FastAPI
dependency override) so these tests never touch real seed data and
never make a live network call regardless of the developer's real
.env/GEMINI_API_KEY.
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

GROUND_TRUTH_FIELDS = [
    "expected_fault",
    "expected_evidence",
    "expected_next_command",
    "expected_fix",
    "verification_command",
]


def _seed_case_row(case_id, source="seed", **overrides):
    row = {
        "case_id": case_id,
        "title": f"Practice test case {case_id}",
        "symptom": "PC cannot reach the file server after a recent change.",
        "topology_note": "PC1 connects to SW1 Fa0/3, SW1 uplinks to R1.",
        "show_outputs": "show vlan brief\nVLAN 10 Sales active Fa0/3\nVLAN 20 Eng active Fa0/4",
        "expected_fault": "Fa0/3 is assigned to VLAN 20 instead of VLAN 10.",
        "osi_layer": "Layer 2",
        "concept": "VLAN",
        "severity": "Medium",
        "expected_evidence": "show vlan brief confirms Fa0/3 is in VLAN 20.",
        "expected_next_command": "show interfaces fa0/3 switchport",
        "expected_fix": "switchport access vlan 10",
        "verification_command": "ping the file server from PC1",
        "difficulty": "Easy",
        "status": "active",
        "source": source,
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-01T00:00:00Z",
        "created_by": "Course Dataset" if source == "seed" else "Test Instructor",
    }
    row.update(overrides)
    return row


@pytest.fixture(autouse=True)
def isolated_cases_csv(monkeypatch, tmp_path):
    temp_csv = tmp_path / "cases.csv"
    with open(temp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=case_service.FIELDS)
        writer.writeheader()
        writer.writerow(_seed_case_row("PRACTICE-SEED-001", source="seed"))
        writer.writerow(_seed_case_row("CASE-9001", source="user"))
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
# Redaction over real HTTP - the safety-critical requirement
# --------------------------------------------------------------------------
def test_practice_case_view_status_and_shape(client):
    r = client.get("/api/practice/cases/PRACTICE-SEED-001")
    assert r.status_code == 200
    data = r.json()
    assert data["case_id"] == "PRACTICE-SEED-001"
    assert data["symptom"] == "PC cannot reach the file server after a recent change."
    assert data["show_outputs"] != ""
    assert data["topology_note"] != ""


def test_practice_case_view_never_leaks_ground_truth_fields(client):
    r = client.get("/api/practice/cases/PRACTICE-SEED-001")
    data = r.json()
    leaked = [f for f in GROUND_TRUTH_FIELDS if f in data]
    assert leaked == [], f"Ground truth leaked via HTTP: {leaked}"


def test_practice_case_view_ground_truth_text_absent_from_raw_response(client):
    """Paranoid check over the literal HTTP response body, not just the
    parsed JSON keys - catches leakage even if a field were renamed."""
    r = client.get("/api/practice/cases/PRACTICE-SEED-001")
    full_case_resp = client.get("/api/cases/PRACTICE-SEED-001")
    full_case = full_case_resp.json()
    for field in GROUND_TRUTH_FIELDS:
        value = full_case[field]
        assert value not in r.text, f"{field}'s value found in raw practice response body"


def test_practice_case_view_404_for_nonexistent_case(client):
    r = client.get("/api/practice/cases/NOPE-9999")
    assert r.status_code == 404


def test_practice_case_view_works_for_user_created_case(client):
    """A case created through the normal case-management API must be
    just as protected in Practice Mode as a seed case - no special
    casing based on `source`."""
    r = client.get("/api/practice/cases/CASE-9001")
    assert r.status_code == 200
    data = r.json()
    leaked = [f for f in GROUND_TRUTH_FIELDS if f in data]
    assert leaked == []


# --------------------------------------------------------------------------
# Submission validation
# --------------------------------------------------------------------------
def test_submit_missing_case_id_rejected(client):
    r = client.post("/api/practice/submit", json={"student_root_cause": "x"})
    assert r.status_code == 422


def test_submit_blank_root_cause_rejected(client):
    r = client.post(
        "/api/practice/submit",
        json={"case_id": "PRACTICE-SEED-001", "student_root_cause": "   "},
    )
    assert r.status_code == 422


def test_submit_missing_root_cause_rejected(client):
    r = client.post("/api/practice/submit", json={"case_id": "PRACTICE-SEED-001"})
    assert r.status_code == 422


def test_submit_nonexistent_case_404(client):
    r = client.post(
        "/api/practice/submit",
        json={"case_id": "NOPE-9999", "student_root_cause": "a hypothesis"},
    )
    assert r.status_code == 404


def test_submit_default_student_name(client):
    r = client.post(
        "/api/practice/submit",
        json={"case_id": "PRACTICE-SEED-001", "student_root_cause": "a hypothesis"},
    )
    assert r.status_code == 200
    summary = client.get("/api/workspace/summary?student_name=Anonymous").json()
    assert summary["completed_count"] >= 1


# --------------------------------------------------------------------------
# Full submission -> comparison flow
# --------------------------------------------------------------------------
def test_submit_valid_returns_full_comparison(client):
    r = client.post(
        "/api/practice/submit",
        json={
            "case_id": "PRACTICE-SEED-001",
            "student_name": "Alice",
            "student_root_cause": "The switchport is in the wrong VLAN",
            "student_osi_layer": "Layer 2",
            "student_next_command": "show vlan brief",
            "student_fix": "reassign the port to VLAN 10",
        },
    )
    assert r.status_code == 200
    data = r.json()

    assert data["student_root_cause"] == "The switchport is in the wrong VLAN"
    assert data["student_osi_layer"] == "Layer 2"

    assert data["mock_mode"] is True
    assert data["ai_root_cause"] is not None

    assert data["expected_fault"] == "Fa0/3 is assigned to VLAN 20 instead of VLAN 10."
    assert data["expected_fix"] == "switchport access vlan 10"
    assert data["verification_command"] == "ping the file server from PC1"

    assert data["human_review_required"] is True
    assert "advisory" in data["safety_notice"].lower()
    assert "heuristic" in data["safety_notice"].lower() or "learning aid" in data["safety_notice"].lower()

    assert "rule_findings_count" in data
    assert isinstance(data["rule_findings_count"], int)

    assert isinstance(data["student_matches_expected_concept"], bool)
    assert isinstance(data["ai_matches_expected_concept"], bool)


def test_submit_works_for_user_created_case(client):
    """The explicit requirement: newly created cases work in Practice
    Mode with no special-casing - same endpoint, same pipeline."""
    r = client.post(
        "/api/practice/submit",
        json={
            "case_id": "CASE-9001",
            "student_name": "Bob",
            "student_root_cause": "A hypothesis about the user-created case",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["case_id"] == "CASE-9001"
    assert data["expected_fault"] != ""
    assert data["mock_mode"] is True


def test_submit_verbatim_expected_answer_matches(client):
    r = client.post(
        "/api/practice/submit",
        json={
            "case_id": "PRACTICE-SEED-001",
            "student_root_cause": "Fa0/3 is assigned to VLAN 20 instead of VLAN 10.",
        },
    )
    data = r.json()
    assert data["student_matches_expected_concept"] is True


def test_submit_unrelated_answer_does_not_match(client):
    r = client.post(
        "/api/practice/submit",
        json={
            "case_id": "PRACTICE-SEED-001",
            "student_root_cause": "This is about a totally different NAT overload problem",
        },
    )
    data = r.json()
    assert data["student_matches_expected_concept"] is False


# --------------------------------------------------------------------------
# Attempt persistence / completion integration
# --------------------------------------------------------------------------
def test_submit_persists_completed_attempt(client):
    client.post(
        "/api/practice/submit",
        json={
            "case_id": "PRACTICE-SEED-001",
            "student_name": "Carol",
            "student_root_cause": "my hypothesis",
        },
    )
    attempts = client.get("/api/attempts?student_name=Carol").json()["attempts"]
    assert len(attempts) == 1
    assert attempts[0]["status"] == "COMPLETED"
    assert attempts[0]["case_id"] == "PRACTICE-SEED-001"
    assert attempts[0]["student_root_cause"] == "my hypothesis"


def test_submit_reflected_in_workspace_summary(client):
    client.post(
        "/api/practice/submit",
        json={
            "case_id": "PRACTICE-SEED-001",
            "student_name": "Dave",
            "student_root_cause": "my hypothesis",
        },
    )
    summary = client.get("/api/workspace/summary?student_name=Dave").json()
    assert summary["completed_count"] == 1
    assert "PRACTICE-SEED-001" in summary["completed_case_ids"]


def test_submit_reflected_in_case_status_map(client):
    client.post(
        "/api/practice/submit",
        json={
            "case_id": "PRACTICE-SEED-001",
            "student_name": "Erin",
            "student_root_cause": "my hypothesis",
        },
    )
    status_map = client.get("/api/workspace/case-status?student_name=Erin").json()["case_status"]
    assert status_map["PRACTICE-SEED-001"] == "completed"


def test_resubmitting_same_case_creates_new_completed_attempt(client):
    """Practicing a case again after already completing it is a
    legitimate 'try again' flow, not blocked."""
    payload = {
        "case_id": "PRACTICE-SEED-001",
        "student_name": "Frank",
        "student_root_cause": "first attempt",
    }
    client.post("/api/practice/submit", json=payload)
    payload["student_root_cause"] = "second attempt"
    client.post("/api/practice/submit", json=payload)

    attempts = client.get("/api/attempts?student_name=Frank").json()["attempts"]
    assert len(attempts) == 2
    assert all(a["status"] == "COMPLETED" for a in attempts)


# --------------------------------------------------------------------------
# AI diagnosis integration (mock mode, via the shared client fixture)
# --------------------------------------------------------------------------
def test_ai_diagnosis_runs_through_normal_pipeline(client):
    """Confirms the AI diagnosis in the practice response isn't
    fabricated separately - it should reflect the same evidence-based
    reasoning /api/diagnose would produce for this case."""
    r = client.post(
        "/api/practice/submit",
        json={"case_id": "PRACTICE-SEED-001", "student_root_cause": "my hypothesis"},
    )
    practice_ai = r.json()["ai_root_cause"]

    diagnose_resp = client.post("/api/diagnose", json={"case_id": "PRACTICE-SEED-001"})
    direct_ai = diagnose_resp.json()["ai_diagnosis"]["root_cause"]

    # Mock mode is deterministic per case_id, so both call paths should
    # produce the identical grounded diagnosis for the same case.
    assert practice_ai == direct_ai
