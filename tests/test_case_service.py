"""
Tests for case_service's write operations (create/update/archive/restore)
and read-side filtering/search. Every test here points the service at a
throwaway CSV via monkeypatch, so the real data/cases.csv seed data is
never touched by running the test suite.
"""
import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services import case_service


SAMPLE_FIELDS = {
    "title": "Sample test case",
    "symptom": "Sample symptom text",
    "topology_note": "Sample topology",
    "show_outputs": "show ip route\nsample output",
    "expected_fault": "Sample fault",
    "osi_layer": "Layer 3",
    "concept": "Routing",
    "severity": "Low",
    "expected_evidence": "Sample evidence",
    "expected_next_command": "show ip route",
    "expected_fix": "Sample fix",
    "verification_command": "ping test",
    "difficulty": "Easy",
}


@pytest.fixture(autouse=True)
def isolated_cases_csv(monkeypatch, tmp_path):
    """Point case_service at a throwaway CSV, seeded with two rows that
    mimic the real dataset's shape, for every test in this file."""
    temp_csv = tmp_path / "cases.csv"
    with open(temp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=case_service.FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "SEED-001",
                "title": "Seed case one",
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
        writer.writerow(
            {
                "case_id": "SEED-002",
                "title": "Seed case two - VLAN issue",
                "symptom": "Another seed symptom",
                "topology_note": "Seed topology 2",
                "show_outputs": "show vlan brief\nseed output 2",
                "expected_fault": "Seed fault 2",
                "osi_layer": "Layer 2",
                "concept": "VLAN",
                "severity": "High",
                "expected_evidence": "Seed evidence 2",
                "expected_next_command": "show vlan brief",
                "expected_fix": "Seed fix 2",
                "verification_command": "ping seed 2",
                "difficulty": "Hard",
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


# --------------------------------------------------------------------------
# Backward compatibility: list_cases() with no args behaves as before
# --------------------------------------------------------------------------
def test_list_cases_no_args_returns_active_seed_cases():
    cases = case_service.list_cases()
    assert len(cases) == 2
    assert {c["case_id"] for c in cases} == {"SEED-001", "SEED-002"}


def test_get_case_unchanged_signature():
    case = case_service.get_case("SEED-001")
    assert case["title"] == "Seed case one"


def test_get_case_not_found_raises():
    with pytest.raises(case_service.CaseNotFoundError):
        case_service.get_case("DOES-NOT-EXIST")


def test_summary_counts_unchanged_shape():
    summary = case_service.summary_counts()
    assert summary["total_cases"] == 2
    assert summary["by_concept"] == {"Routing": 1, "VLAN": 1}


# --------------------------------------------------------------------------
# Create
# --------------------------------------------------------------------------
def test_create_case_persists_and_is_immediately_listed():
    before = len(case_service.list_cases())
    created = case_service.create_case(SAMPLE_FIELDS, created_by="Test Instructor")

    assert created["case_id"].startswith("CASE-")
    assert created["source"] == "user"
    assert created["status"] == "active"
    assert created["created_by"] == "Test Instructor"
    assert created["title"] == "Sample test case"

    after = case_service.list_cases()
    assert len(after) == before + 1
    assert any(c["case_id"] == created["case_id"] for c in after)


def test_create_case_is_fetchable_via_get_case():
    created = case_service.create_case(SAMPLE_FIELDS)
    fetched = case_service.get_case(created["case_id"])
    assert fetched["symptom"] == "Sample symptom text"


def test_create_case_ids_increment_and_are_unique():
    c1 = case_service.create_case(SAMPLE_FIELDS)
    c2 = case_service.create_case(SAMPLE_FIELDS)
    assert c1["case_id"] != c2["case_id"]


def test_create_case_default_author_when_blank():
    created = case_service.create_case(SAMPLE_FIELDS, created_by="")
    assert created["created_by"] == "Anonymous"


def test_create_case_does_not_affect_seed_cases():
    case_service.create_case(SAMPLE_FIELDS)
    seed_cases = [c for c in case_service.list_cases() if c["source"] == "seed"]
    assert len(seed_cases) == 2


# --------------------------------------------------------------------------
# Update
# --------------------------------------------------------------------------
def test_update_case_changes_only_specified_fields():
    created = case_service.create_case(SAMPLE_FIELDS)
    updated = case_service.update_case(created["case_id"], {"title": "New title"})
    assert updated["title"] == "New title"
    assert updated["symptom"] == SAMPLE_FIELDS["symptom"]  # unchanged


def test_update_case_preserves_identity_fields():
    created = case_service.create_case(SAMPLE_FIELDS)
    updated = case_service.update_case(created["case_id"], {"title": "Changed"})
    assert updated["case_id"] == created["case_id"]
    assert updated["source"] == created["source"]
    assert updated["created_at"] == created["created_at"]


def test_update_seed_case_works():
    updated = case_service.update_case("SEED-001", {"title": "Corrected seed title"})
    assert updated["title"] == "Corrected seed title"
    assert updated["source"] == "seed"


def test_update_nonexistent_case_raises():
    with pytest.raises(case_service.CaseNotFoundError):
        case_service.update_case("NOPE", {"title": "x"})


# --------------------------------------------------------------------------
# Archive / restore (soft delete)
# --------------------------------------------------------------------------
def test_archive_removes_from_default_listing():
    created = case_service.create_case(SAMPLE_FIELDS)
    case_service.set_case_status(created["case_id"], "archived")

    active = case_service.list_cases()
    assert created["case_id"] not in [c["case_id"] for c in active]


def test_archive_does_not_physically_delete():
    created = case_service.create_case(SAMPLE_FIELDS)
    case_service.set_case_status(created["case_id"], "archived")

    # Still fetchable directly - review history referencing this
    # case_id must never 404 just because the case was archived.
    fetched = case_service.get_case(created["case_id"])
    assert fetched["status"] == "archived"

    # Still visible with include_archived=True.
    all_cases = case_service.list_cases(include_archived=True)
    assert created["case_id"] in [c["case_id"] for c in all_cases]


def test_restore_brings_case_back_to_default_listing():
    created = case_service.create_case(SAMPLE_FIELDS)
    case_service.set_case_status(created["case_id"], "archived")
    case_service.set_case_status(created["case_id"], "active")

    active = case_service.list_cases()
    assert created["case_id"] in [c["case_id"] for c in active]


def test_set_case_status_invalid_value_raises():
    created = case_service.create_case(SAMPLE_FIELDS)
    with pytest.raises(ValueError):
        case_service.set_case_status(created["case_id"], "deleted")


def test_set_case_status_nonexistent_case_raises():
    with pytest.raises(case_service.CaseNotFoundError):
        case_service.set_case_status("NOPE", "archived")


# --------------------------------------------------------------------------
# Filtering / search
# --------------------------------------------------------------------------
def test_filter_by_concept():
    results = case_service.list_cases(concept="VLAN")
    assert len(results) == 1
    assert results[0]["case_id"] == "SEED-002"


def test_filter_by_severity():
    results = case_service.list_cases(severity="High")
    assert len(results) == 1
    assert results[0]["case_id"] == "SEED-002"


def test_filter_by_osi_layer():
    results = case_service.list_cases(osi_layer="Layer 2")
    assert len(results) == 1
    assert results[0]["case_id"] == "SEED-002"


def test_filter_by_difficulty():
    results = case_service.list_cases(difficulty="Hard")
    assert len(results) == 1
    assert results[0]["case_id"] == "SEED-002"


def test_search_matches_title():
    results = case_service.list_cases(search="vlan")
    assert len(results) == 1
    assert results[0]["case_id"] == "SEED-002"


def test_search_matches_case_id():
    results = case_service.list_cases(search="seed-001")
    assert len(results) == 1
    assert results[0]["case_id"] == "SEED-001"


def test_search_matches_symptom():
    results = case_service.list_cases(search="Another seed")
    assert len(results) == 1
    assert results[0]["case_id"] == "SEED-002"


def test_filters_combine_with_and():
    results = case_service.list_cases(concept="VLAN", severity="Medium")
    assert results == []


def test_distinct_facet_values():
    facets = case_service.distinct_facet_values()
    assert facets["concepts"] == ["Routing", "VLAN"]
    assert facets["severities"] == ["High", "Medium"]
    assert facets["osi_layers"] == ["Layer 2", "Layer 3"]
    assert facets["difficulties"] == ["Hard", "Medium"]


def test_archived_cases_excluded_from_facets():
    created = case_service.create_case({**SAMPLE_FIELDS, "concept": "UniqueConceptXYZ"})
    case_service.set_case_status(created["case_id"], "archived")
    facets = case_service.distinct_facet_values()
    assert "UniqueConceptXYZ" not in facets["concepts"]
