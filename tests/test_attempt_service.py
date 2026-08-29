"""
Tests for attempt_service (Student Workspace progress tracking).
Every test points the service at an isolated temp CSV via monkeypatch,
so the real data/attempts.csv (if it exists at all - it's created
lazily on first use) is never touched.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services import attempt_service


@pytest.fixture(autouse=True)
def isolated_attempts_csv(monkeypatch, tmp_path):
    temp_csv = tmp_path / "attempts.csv"
    monkeypatch.setattr(attempt_service, "ATTEMPTS_CSV_PATH", str(temp_csv))
    yield


def test_list_attempts_empty_when_no_file():
    assert attempt_service.list_attempts() == []


def test_start_attempt_creates_in_progress_record():
    a = attempt_service.start_attempt("VLAN-001", "Alice")
    assert a["case_id"] == "VLAN-001"
    assert a["student_name"] == "Alice"
    assert a["status"] == "IN_PROGRESS"
    assert a["started_at"] != ""
    assert a["completed_at"] == ""


def test_start_attempt_persists():
    attempt_service.start_attempt("VLAN-001", "Alice")
    assert len(attempt_service.list_attempts()) == 1


def test_restarting_same_case_same_student_deduplicates():
    a1 = attempt_service.start_attempt("VLAN-001", "Alice")
    a2 = attempt_service.start_attempt("VLAN-001", "Alice")
    assert a1["attempt_id"] == a2["attempt_id"]
    assert len(attempt_service.list_attempts()) == 1


def test_different_student_same_case_gets_separate_attempt():
    a1 = attempt_service.start_attempt("VLAN-001", "Alice")
    a2 = attempt_service.start_attempt("VLAN-001", "Bob")
    assert a1["attempt_id"] != a2["attempt_id"]
    assert len(attempt_service.list_attempts()) == 2


def test_student_name_matching_is_case_insensitive():
    a1 = attempt_service.start_attempt("VLAN-001", "Alice")
    a2 = attempt_service.start_attempt("VLAN-001", "alice")
    assert a1["attempt_id"] == a2["attempt_id"]


def test_blank_student_name_defaults_to_anonymous():
    a = attempt_service.start_attempt("VLAN-001", "")
    assert a["student_name"] == "Anonymous"


def test_completing_same_case_again_after_completion_starts_new_attempt():
    a1 = attempt_service.start_attempt("VLAN-001", "Alice")
    attempt_service.complete_attempt(a1["attempt_id"])
    # Re-attempting a COMPLETED case is a legitimate "practice again"
    # scenario, not a dedupe case (dedup only applies to IN_PROGRESS).
    a2 = attempt_service.start_attempt("VLAN-001", "Alice")
    assert a2["attempt_id"] != a1["attempt_id"]
    assert len(attempt_service.list_attempts()) == 2


def test_complete_attempt_sets_status_and_timestamp():
    a = attempt_service.start_attempt("VLAN-001", "Alice")
    completed = attempt_service.complete_attempt(a["attempt_id"])
    assert completed["status"] == "COMPLETED"
    assert completed["completed_at"] != ""


def test_complete_attempt_records_practice_mode_fields():
    a = attempt_service.start_attempt("VLAN-001", "Alice")
    completed = attempt_service.complete_attempt(
        a["attempt_id"],
        student_root_cause="Wrong VLAN on the port",
        student_osi_layer="Layer 2",
        student_next_command="show vlan brief",
        student_fix="switchport access vlan 10",
        ai_root_cause="Port is in VLAN 20 instead of VLAN 10",
        matches_expected_concept=True,
    )
    assert completed["student_root_cause"] == "Wrong VLAN on the port"
    assert completed["student_osi_layer"] == "Layer 2"
    assert completed["ai_root_cause"] == "Port is in VLAN 20 instead of VLAN 10"
    assert completed["matches_expected_concept"] == "True"


def test_complete_nonexistent_attempt_raises():
    with pytest.raises(attempt_service.AttemptNotFoundError):
        attempt_service.complete_attempt("ATT-9999")


def test_get_attempt_not_found_raises():
    with pytest.raises(attempt_service.AttemptNotFoundError):
        attempt_service.get_attempt("ATT-9999")


def test_get_attempt_found():
    a = attempt_service.start_attempt("VLAN-001", "Alice")
    fetched = attempt_service.get_attempt(a["attempt_id"])
    assert fetched["attempt_id"] == a["attempt_id"]


def test_attempt_ids_increment():
    a1 = attempt_service.start_attempt("VLAN-001", "Alice")
    a2 = attempt_service.start_attempt("DHCP-001", "Bob")
    n1 = int(a1["attempt_id"].split("-")[1])
    n2 = int(a2["attempt_id"].split("-")[1])
    assert n2 > n1


def test_list_attempts_for_student_filters_correctly():
    attempt_service.start_attempt("VLAN-001", "Alice")
    attempt_service.start_attempt("DHCP-001", "Bob")
    attempt_service.start_attempt("ACL-001", "Alice")

    alice_attempts = attempt_service.list_attempts_for_student("Alice")
    assert len(alice_attempts) == 2
    assert {a["case_id"] for a in alice_attempts} == {"VLAN-001", "ACL-001"}


def test_student_summary_counts_attempted_and_completed_separately():
    a1 = attempt_service.start_attempt("VLAN-001", "Alice")
    attempt_service.start_attempt("DHCP-001", "Alice")
    attempt_service.complete_attempt(a1["attempt_id"])

    summary = attempt_service.student_summary("Alice")
    assert summary["attempted_count"] == 2
    assert summary["completed_count"] == 1
    assert summary["in_progress_case_ids"] == ["DHCP-001"]
    assert summary["completed_case_ids"] == ["VLAN-001"]


def test_student_summary_empty_for_student_with_no_attempts():
    summary = attempt_service.student_summary("Nobody")
    assert summary["attempted_count"] == 0
    assert summary["completed_count"] == 0
    assert summary["attempted_case_ids"] == []


def test_attempts_for_different_students_are_independent():
    a1 = attempt_service.start_attempt("VLAN-001", "Alice")
    attempt_service.start_attempt("VLAN-001", "Bob")
    attempt_service.complete_attempt(a1["attempt_id"])

    alice_summary = attempt_service.student_summary("Alice")
    bob_summary = attempt_service.student_summary("Bob")
    assert alice_summary["completed_count"] == 1
    assert bob_summary["completed_count"] == 0
    assert bob_summary["attempted_count"] == 1
