"""
API-level tests for case management (POST/PATCH /api/cases/...).
Uses an isolated temp CSV (via monkeypatch on case_service.CASES_CSV_PATH)
so these tests never touch the real data/cases.csv seed data - the same
isolation pattern test_api.py uses for reviews.csv.
"""
import csv
import os
import sys

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND_DIR = os.path.join(_PROJECT_ROOT, "backend")
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, _BACKEND_DIR)

from backend.services import case_service

VALID_CASE_PAYLOAD = {
    "title": "API test case",
    "symptom": "API test symptom",
    "topology_note": "API test topology",
    "show_outputs": "show ip route\napi test output",
    "expected_fault": "API test fault",
    "osi_layer": "Layer 3",
    "concept": "Routing",
    "severity": "Low",
    "expected_evidence": "API test evidence",
    "expected_next_command": "show ip route",
    "expected_fix": "API test fix",
    "verification_command": "ping test",
    "difficulty": "Easy",
    "created_by": "API Tester",
}


@pytest.fixture(autouse=True)
def isolated_cases_csv(monkeypatch, tmp_path):
    """Seed a throwaway cases.csv with a couple of rows mimicking the
    real dataset's shape, and point case_service at it for every test
    in this file."""
    temp_csv = tmp_path / "cases.csv"
    with open(temp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=case_service.FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "SEED-API-001",
                "title": "Seed API case",
                "symptom": "Seed symptom",
                "topology_note": "Seed topology",
                "show_outputs": "show ip route\nseed output",
                "expected_fault": "Seed fault",
                "osi_layer": "Layer 3",
                "concept": "Routing",
                "severity": "Medium",
                "expected_evidence": "Seed evidence",
                "expected_next_command": "show ip route",
                "expected_fix": "Seed fix",
                "verification_command": "ping seed",
                "difficulty": "Medium",
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
def isolated_reviews_csv(monkeypatch, tmp_path):
    """Also isolate reviews.csv, since /api/diagnose -> review flow is
    exercised in the pipeline-integration test below."""
    from backend.services import review_service

    temp_csv = tmp_path / "reviews.csv"
    monkeypatch.setattr(review_service, "REVIEWS_CSV_PATH", str(temp_csv))
    yield


# NOTE: the `client` fixture used throughout this file is defined once,
# shared, in tests/conftest.py - it forces AI-diagnosis mock mode via a
# FastAPI dependency override so these tests behave identically whether
# or not a real GEMINI_API_KEY is set in the actual environment pytest
# runs in. See conftest.py's module docstring. This
# file's autouse isolated_cases_csv/isolated_reviews_csv fixtures above
# are function-scoped just like `client`, so pytest runs all of them
# for every test regardless of which file each is defined in - no
# special ordering is needed here.


# --------------------------------------------------------------------------
# Backward compatibility
# --------------------------------------------------------------------------
def test_get_cases_no_params_unchanged(client):
    r = client.get("/api/cases")
    assert r.status_code == 200
    assert len(r.json()["cases"]) == 1
    assert r.json()["cases"][0]["case_id"] == "SEED-API-001"


def test_get_case_detail_unchanged(client):
    r = client.get("/api/cases/SEED-API-001")
    assert r.status_code == 200
    assert r.json()["title"] == "Seed API case"


def test_get_case_detail_404_unchanged(client):
    r = client.get("/api/cases/NOPE")
    assert r.status_code == 404


# --------------------------------------------------------------------------
# Facets route must not be swallowed by /{case_id}
# --------------------------------------------------------------------------
def test_facets_route_resolves_correctly(client):
    r = client.get("/api/cases/facets")
    assert r.status_code == 200
    data = r.json()
    assert "concepts" in data
    assert "Routing" in data["concepts"]


# --------------------------------------------------------------------------
# Create
# --------------------------------------------------------------------------
def test_create_case_success(client):
    r = client.post("/api/cases", json=VALID_CASE_PAYLOAD)
    assert r.status_code == 200
    case = r.json()["case"]
    assert case["case_id"].startswith("CASE-")
    assert case["source"] == "user"
    assert case["status"] == "active"
    assert case["created_by"] == "API Tester"


def test_create_case_immediately_listed(client):
    client.post("/api/cases", json=VALID_CASE_PAYLOAD)
    r = client.get("/api/cases")
    assert len(r.json()["cases"]) == 2


def test_create_case_blank_title_rejected(client):
    payload = dict(VALID_CASE_PAYLOAD, title="   ")
    r = client.post("/api/cases", json=payload)
    assert r.status_code == 422


def test_create_case_invalid_severity_rejected(client):
    payload = dict(VALID_CASE_PAYLOAD, severity="Extreme")
    r = client.post("/api/cases", json=payload)
    assert r.status_code == 422


def test_create_case_missing_required_field_rejected(client):
    payload = dict(VALID_CASE_PAYLOAD)
    del payload["symptom"]
    r = client.post("/api/cases", json=payload)
    assert r.status_code == 422


# --------------------------------------------------------------------------
# Full pipeline integration: a created case works exactly like a seed one
# --------------------------------------------------------------------------
def test_created_case_works_through_full_pipeline(client):
    create_resp = client.post("/api/cases", json=VALID_CASE_PAYLOAD)
    case_id = create_resp.json()["case"]["case_id"]

    check_resp = client.post("/api/check", json={"case_id": case_id})
    assert check_resp.status_code == 200
    assert "findings" in check_resp.json()

    diagnose_resp = client.post("/api/diagnose", json={"case_id": case_id})
    assert diagnose_resp.status_code == 200
    data = diagnose_resp.json()
    assert data["mock_mode"] is True
    assert data["ai_diagnosis"] is not None
    assert data["human_review_required"] is True

    review_resp = client.post(
        "/api/reviews",
        json={
            "case_id": case_id,
            "ai_root_cause": data["ai_diagnosis"]["root_cause"],
            "ai_confidence": data["ai_diagnosis"]["confidence"],
            "human_decision": "ACCEPTED",
            "reviewer": "API Test Reviewer",
        },
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["review"]["case_id"] == case_id


# --------------------------------------------------------------------------
# Update
# --------------------------------------------------------------------------
def test_update_case_success(client):
    create_resp = client.post("/api/cases", json=VALID_CASE_PAYLOAD)
    case_id = create_resp.json()["case"]["case_id"]

    r = client.patch(f"/api/cases/{case_id}", json={"title": "Updated title"})
    assert r.status_code == 200
    assert r.json()["case"]["title"] == "Updated title"


def test_update_case_preserves_untouched_fields(client):
    create_resp = client.post("/api/cases", json=VALID_CASE_PAYLOAD)
    case_id = create_resp.json()["case"]["case_id"]

    r = client.patch(f"/api/cases/{case_id}", json={"title": "New title"})
    assert r.json()["case"]["symptom"] == VALID_CASE_PAYLOAD["symptom"]


def test_update_nonexistent_case_404(client):
    r = client.patch("/api/cases/NOPE-9999", json={"title": "x"})
    assert r.status_code == 404


def test_update_seed_case_works(client):
    r = client.patch("/api/cases/SEED-API-001", json={"title": "Corrected"})
    assert r.status_code == 200
    assert r.json()["case"]["title"] == "Corrected"
    assert r.json()["case"]["source"] == "seed"


# --------------------------------------------------------------------------
# Archive / restore
# --------------------------------------------------------------------------
def test_archive_then_restore(client):
    create_resp = client.post("/api/cases", json=VALID_CASE_PAYLOAD)
    case_id = create_resp.json()["case"]["case_id"]

    archive_resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "archived"})
    assert archive_resp.status_code == 200
    assert archive_resp.json()["case"]["status"] == "archived"

    list_resp = client.get("/api/cases")
    assert case_id not in [c["case_id"] for c in list_resp.json()["cases"]]

    detail_resp = client.get(f"/api/cases/{case_id}")
    assert detail_resp.status_code == 200  # still directly fetchable

    restore_resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "active"})
    assert restore_resp.status_code == 200
    assert restore_resp.json()["case"]["status"] == "active"

    list_resp_2 = client.get("/api/cases")
    assert case_id in [c["case_id"] for c in list_resp_2.json()["cases"]]


def test_archive_nonexistent_case_404(client):
    r = client.patch("/api/cases/NOPE-9999/status", json={"status": "archived"})
    assert r.status_code == 404


def test_invalid_status_value_rejected(client):
    create_resp = client.post("/api/cases", json=VALID_CASE_PAYLOAD)
    case_id = create_resp.json()["case"]["case_id"]
    r = client.patch(f"/api/cases/{case_id}/status", json={"status": "deleted"})
    assert r.status_code == 422


# --------------------------------------------------------------------------
# Filtering
# --------------------------------------------------------------------------
def test_filter_by_concept_via_api(client):
    client.post("/api/cases", json=dict(VALID_CASE_PAYLOAD, concept="DNS"))
    r = client.get("/api/cases?concept=DNS")
    assert len(r.json()["cases"]) == 1
    assert r.json()["cases"][0]["concept"] == "DNS"


def test_search_via_api(client):
    r = client.get("/api/cases?search=seed")
    assert len(r.json()["cases"]) == 1
    assert r.json()["cases"][0]["case_id"] == "SEED-API-001"
