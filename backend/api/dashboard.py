from __future__ import annotations

from fastapi import APIRouter

from backend.services.case_service import list_cases, summary_counts
from backend.services.review_service import agreement_stats, list_reviews
from backend.services.attempt_service import all_students_progress_summary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard():
    case_summary = summary_counts()
    review_summary = agreement_stats()
    reviews = list_reviews()

    decision_counts = {
        "ACCEPTED": review_summary["accepted"],
        "EDITED": review_summary["edited"],
        "REJECTED": review_summary["rejected"],
    }

    # Aggregate deterministic rule-checker rule hit counts across the
    # whole dataset, for the "Rule-checker findings" chart.
    from backend.rules.checker import run_checks

    rule_hit_counts: dict = {}
    for case in list_cases():
        for finding in run_checks(case):
            rule_hit_counts[finding.rule] = rule_hit_counts.get(finding.rule, 0) + 1

    return {
        "total_cases": case_summary["total_cases"],
        "cases_by_concept": case_summary["by_concept"],
        "cases_by_severity": case_summary["by_severity"],
        "cases_by_osi_layer": case_summary["by_osi_layer"],
        "reviewed": review_summary["total_reviewed"],
        "decision_counts": decision_counts,
        "agreement_rate_percent": review_summary["agreement_rate_percent"],
        "average_ai_confidence": review_summary["average_ai_confidence"],
        "corrections_by_concept": review_summary["corrections_by_concept"],
        "corrections_by_severity": review_summary["corrections_by_severity"],
        "rule_hit_counts": rule_hit_counts,
        "recent_reviews": list(reversed(reviews))[:10],
        "student_progress": all_students_progress_summary(),
        "safety_notice": (
            "AI recommendations are advisory. A human reviewer must "
            "approve every diagnosis before a fix is accepted."
        ),
    }
