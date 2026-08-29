"""
Review service - the Responsible AI log. Reads and appends to
data/reviews.csv. This is the only file in the app that the running
backend writes to; everything else (cases.csv) is read-only course data.
"""
from __future__ import annotations

import csv
import os
import threading
from datetime import datetime, timezone
from typing import List

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
REVIEWS_CSV_PATH = os.path.join(PROJECT_ROOT, "data", "reviews.csv")

FIELDS = [
    "review_id", "case_id", "ai_root_cause", "ai_confidence",
    "human_decision", "human_root_cause", "correction_reason",
    "reviewer", "timestamp", "verification_status", "evidence_missed",
]

_write_lock = threading.Lock()


def list_reviews() -> List[dict]:
    if not os.path.exists(REVIEWS_CSV_PATH):
        return []
    with open(REVIEWS_CSV_PATH, newline="", encoding="utf-8") as f:
        rows = []
        for row in csv.DictReader(f):
            row = dict(row)
            row.setdefault("verification_status", "NOT_VERIFIED")
            row.setdefault("evidence_missed", "")
            rows.append(row)
        return rows


def _next_review_id(existing: List[dict]) -> str:
    max_n = 0
    for row in existing:
        rid = row.get("review_id", "")
        if rid.startswith("REV-"):
            try:
                max_n = max(max_n, int(rid.split("-")[1]))
            except (IndexError, ValueError):
                continue
    return f"REV-{max_n + 1:04d}"


def create_review(
    case_id: str,
    ai_root_cause: str,
    ai_confidence: float,
    human_decision: str,
    human_root_cause: str = "",
    correction_reason: str = "",
    reviewer: str = "Anonymous Reviewer",
) -> dict:
    """Append a new review row. Thread-safe for the simple single-process
    dev server this project targets; not intended as a substitute for a
    real database under concurrent multi-process load."""
    with _write_lock:
        existing = list_reviews()
        review = {
            "review_id": _next_review_id(existing),
            "case_id": case_id,
            "ai_root_cause": ai_root_cause,
            "ai_confidence": ai_confidence,
            "human_decision": human_decision,
            "human_root_cause": human_root_cause,
            "correction_reason": correction_reason,
            "reviewer": reviewer,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "verification_status": "NOT_VERIFIED",
            "evidence_missed": "",
        }
        file_exists = os.path.exists(REVIEWS_CSV_PATH)
        with open(REVIEWS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(review)
        return review

def _write_all(reviews: List[dict]) -> None:
    with open(REVIEWS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in reviews:
            writer.writerow({k: row.get(k, "") for k in FIELDS})

class ReviewNotFoundError(Exception):
    pass

def verify_review(review_id: str, status: str, evidence_missed: str = "") -> dict:
    if status not in ("VERIFIED", "VERIFICATION_FAILED", "NOT_VERIFIED"):
        raise ValueError("Invalid verification status")

    with _write_lock:
        existing = list_reviews()
        found = False
        updated_rows = []
        for row in existing:
            if row["review_id"] == review_id:
                found = True
                updated = dict(row)
                updated["verification_status"] = status
                updated["evidence_missed"] = evidence_missed.strip()
                updated_rows.append(updated)
            else:
                updated_rows.append(row)

        if not found:
            raise ReviewNotFoundError(f"Review '{review_id}' not found")

        _write_all(updated_rows)
        return next(r for r in updated_rows if r["review_id"] == review_id)


def agreement_stats() -> dict:
    reviews = list_reviews()
    total = len(reviews)
    if total == 0:
        return {
            "total_reviewed": 0,
            "accepted": 0,
            "edited": 0,
            "rejected": 0,
            "agreement_rate_percent": 0.0,
            "average_ai_confidence": 0.0,
            "corrections_by_concept": {},
            "corrections_by_severity": {},
        }

    accepted = sum(1 for r in reviews if r["human_decision"] == "ACCEPTED")
    edited = sum(1 for r in reviews if r["human_decision"] == "EDITED")
    rejected = sum(1 for r in reviews if r["human_decision"] == "REJECTED")

    confidences = []
    for r in reviews:
        try:
            confidences.append(float(r["ai_confidence"]))
        except (TypeError, ValueError):
            continue
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Corrections by concept requires joining back to the case dataset,
    # done lazily here to avoid a hard import-time dependency loop.
    from backend.services.case_service import get_case_or_none

    corrections_by_concept: dict = {}
    corrections_by_severity: dict = {}
    for r in reviews:
        if r["human_decision"] in ("EDITED", "REJECTED"):
            case = get_case_or_none(r["case_id"])
            concept = case["concept"] if case else "Unknown"
            severity = case["severity"] if case else "Unknown"
            corrections_by_concept[concept] = corrections_by_concept.get(concept, 0) + 1
            corrections_by_severity[severity] = corrections_by_severity.get(severity, 0) + 1

    return {
        "total_reviewed": total,
        "accepted": accepted,
        "edited": edited,
        "rejected": rejected,
        "agreement_rate_percent": round((accepted / total) * 100, 1),
        "average_ai_confidence": round(avg_confidence, 2),
        "corrections_by_concept": corrections_by_concept,
        "corrections_by_severity": corrections_by_severity,
    }
