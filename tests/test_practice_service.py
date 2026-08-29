"""
Tests for practice_service.py. Two concerns: (1) to_practice_view never
leaks ground-truth fields - this is the safety-critical part of
Practice Mode, so it's tested exhaustively; (2) submit_practice_attempt
correctly runs the rule checker + AI pipeline and records an attempt.

Uses an isolated temp attempts.csv via monkeypatch, and a MockAIClient
explicitly passed in (never relying on environment auto-detection), so
these tests never touch the real data/attempts.csv and never make a
live network call regardless of what's in the developer's real .env.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ai.client import MockAIClient
from backend.services import attempt_service
from backend.services.case_service import list_cases
from backend.services.practice_schemas import PracticeCaseView, PracticeComparisonResult
from backend.services.practice_service import submit_practice_attempt, to_practice_view

GROUND_TRUTH_FIELDS = [
    "expected_fault",
    "expected_evidence",
    "expected_next_command",
    "expected_fix",
    "verification_command",
]


@pytest.fixture(autouse=True)
def isolated_attempts_csv(monkeypatch, tmp_path):
    temp_csv = tmp_path / "attempts.csv"
    monkeypatch.setattr(attempt_service, "ATTEMPTS_CSV_PATH", str(temp_csv))
    yield


# --------------------------------------------------------------------------
# Redaction (safety-critical)
# --------------------------------------------------------------------------
def test_practice_view_returns_expected_type():
    case = list_cases()[0]
    view = to_practice_view(case)
    assert isinstance(view, PracticeCaseView)


def test_practice_view_never_includes_ground_truth_fields():
    case = list_cases()[0]
    view_dict = to_practice_view(case).model_dump()
    for field in GROUND_TRUTH_FIELDS:
        assert field not in view_dict, f"{field} leaked into practice view!"


def test_practice_view_ground_truth_text_never_appears_verbatim():
    """Paranoid check: even if a ground-truth field name isn't a key in
    the view, make sure its VALUE text doesn't leak into an allowed
    field either (e.g. accidentally concatenated into the symptom)."""
    for case in list_cases():
        view_dict = to_practice_view(case).model_dump()
        view_text = " ".join(str(v) for v in view_dict.values())
        for field in GROUND_TRUTH_FIELDS:
            value = case.get(field, "")
            if value and len(value) > 20:  # skip trivially short values that could coincidentally match
                assert value not in view_text, (
                    f"{case['case_id']}: {field}'s value leaked into the practice view text"
                )


def test_practice_view_includes_allowed_fields():
    case = list_cases()[0]
    view = to_practice_view(case)
    assert view.case_id == case["case_id"]
    assert view.symptom == case["symptom"]
    assert view.show_outputs == case["show_outputs"]
    assert view.topology_note == case["topology_note"]


def test_practice_view_works_for_every_seed_case():
    """Run the redaction against the entire real dataset, not just one
    case, to catch any case-specific data issue."""
    for case in list_cases():
        view_dict = to_practice_view(case).model_dump()
        for field in GROUND_TRUTH_FIELDS:
            assert field not in view_dict


# --------------------------------------------------------------------------
# Submission / comparison
# --------------------------------------------------------------------------
def test_submit_practice_attempt_returns_comparison_result():
    case = list_cases()[0]
    result = submit_practice_attempt(
        case,
        student_name="Test Student",
        student_root_cause="my hypothesis",
        student_osi_layer="Layer 2",
        student_next_command="show run",
        student_fix="my fix",
        ai_client=MockAIClient(),
    )
    assert isinstance(result, PracticeComparisonResult)
    assert result.case_id == case["case_id"]


def test_submit_practice_attempt_reveals_ground_truth_after_submission():
    """After submission, the response SHOULD contain the expected
    answer - that's the whole point of the comparison feedback."""
    case = list_cases()[0]
    result = submit_practice_attempt(
        case,
        student_name="Test Student",
        student_root_cause="my hypothesis",
        student_osi_layer="",
        student_next_command="",
        student_fix="",
        ai_client=MockAIClient(),
    )
    assert result.expected_fault == case["expected_fault"]
    assert result.expected_fix == case["expected_fix"]


def test_submit_practice_attempt_includes_ai_diagnosis():
    case = list_cases()[0]
    result = submit_practice_attempt(
        case,
        student_name="Test Student",
        student_root_cause="my hypothesis",
        student_osi_layer="",
        student_next_command="",
        student_fix="",
        ai_client=MockAIClient(),
    )
    assert result.ai_root_cause is not None
    assert result.mock_mode is True


def test_submit_practice_attempt_preserves_student_answer():
    case = list_cases()[0]
    result = submit_practice_attempt(
        case,
        student_name="Test Student",
        student_root_cause="specific student hypothesis text",
        student_osi_layer="Layer 4",
        student_next_command="show run",
        student_fix="a specific fix",
        ai_client=MockAIClient(),
    )
    assert result.student_root_cause == "specific student hypothesis text"
    assert result.student_osi_layer == "Layer 4"
    assert result.student_next_command == "show run"
    assert result.student_fix == "a specific fix"


def test_submit_practice_attempt_always_requires_human_review():
    case = list_cases()[0]
    result = submit_practice_attempt(
        case, "Test Student", "hypothesis", "", "", "", ai_client=MockAIClient()
    )
    assert result.human_review_required is True


def test_submit_practice_attempt_records_completed_attempt():
    case = list_cases()[0]
    submit_practice_attempt(
        case, "Alice", "hypothesis", "", "", "", ai_client=MockAIClient()
    )
    summary = attempt_service.student_summary("Alice")
    assert summary["completed_count"] == 1
    assert case["case_id"] in summary["completed_case_ids"]


def test_submit_practice_attempt_matches_expected_concept_when_verbatim():
    """Using the exact expected_fault text as the student's answer
    should trivially match via the substring heuristic - a sanity
    check that the matching logic isn't inverted or broken."""
    case = list_cases()[0]
    result = submit_practice_attempt(
        case,
        student_name="Test Student",
        student_root_cause=case["expected_fault"],
        student_osi_layer="",
        student_next_command="",
        student_fix="",
        ai_client=MockAIClient(),
    )
    assert result.student_matches_expected_concept is True


def test_submit_practice_attempt_no_match_for_unrelated_answer():
    case = list_cases()[0]
    result = submit_practice_attempt(
        case,
        student_name="Test Student",
        student_root_cause="completely unrelated answer about a different topic entirely",
        student_osi_layer="",
        student_next_command="",
        student_fix="",
        ai_client=MockAIClient(),
    )
    assert result.student_matches_expected_concept is False


def test_submit_practice_attempt_handles_ai_client_error_gracefully():
    """If the AI call fails (e.g. real provider network error), the
    student's own answer and the expected ground truth must still be
    returned - the comparison shouldn't be all-or-nothing."""
    from backend.ai.client import AIClient, AIClientError

    class BrokenClient(AIClient):
        is_mock = False

        def complete(self, system_prompt, user_prompt, case=None):
            raise AIClientError("simulated provider failure")

    case = list_cases()[0]
    result = submit_practice_attempt(
        case,
        student_name="Test Student",
        student_root_cause="my hypothesis",
        student_osi_layer="",
        student_next_command="",
        student_fix="",
        ai_client=BrokenClient(),
    )
    assert result.ai_root_cause is None
    assert result.ai_error is not None
    assert result.expected_fault == case["expected_fault"]
    assert result.student_root_cause == "my hypothesis"
