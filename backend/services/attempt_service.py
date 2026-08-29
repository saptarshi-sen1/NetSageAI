"""
Attempt service - tracks student progress through cases. Reads and
appends to data/attempts.csv, the same CSV-append pattern
review_service.py uses for data/reviews.csv.

An "attempt" is created the moment a student opens a case in the
Student Workspace (status=IN_PROGRESS) and is marked COMPLETED once
they've gone through the case's workflow. In Practice Mode (see
backend/api/practice.py), an attempt additionally records the
student's own hypothesis (root cause / OSI layer / next command / fix)
alongside the AI's diagnosis and the dataset's expected answer, so the
Student Workspace can show "attempted / completed" counts and Practice
Mode can show "your answer vs AI vs expected" feedback from the same
underlying record - no separate parallel system.

This is intentionally NOT a user-authentication system. Per the
project's explicit instruction not to add unnecessary auth, a "student"
here is just a free-text name/identifier the person enters, the same
lightweight-identity pattern review_service.py already uses for
`reviewer`.
"""
from __future__ import annotations

import csv
import os
import threading
from datetime import datetime, timezone
from typing import List, Optional

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
ATTEMPTS_CSV_PATH = os.path.join(PROJECT_ROOT, "data", "attempts.csv")

FIELDS = [
    "attempt_id", "case_id", "student_name", "status",
    "started_at", "completed_at",
    # Practice Mode fields - populated only when the student submits a
    # hypothesis before seeing the AI/expected answer (see practice.py).
    # Left blank for plain Student Workspace attempts (no Practice Mode).
    "student_root_cause", "student_osi_layer", "student_next_command",
    "student_fix", "ai_root_cause", "matches_expected_concept",
]

STATUSES = ("IN_PROGRESS", "COMPLETED")

_write_lock = threading.Lock()


class AttemptNotFoundError(Exception):
    pass


def list_attempts() -> List[dict]:
    if not os.path.exists(ATTEMPTS_CSV_PATH):
        return []
    with open(ATTEMPTS_CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def list_attempts_for_student(student_name: str) -> List[dict]:
    name = student_name.strip().lower()
    return [a for a in list_attempts() if a.get("student_name", "").strip().lower() == name]


def get_attempt(attempt_id: str) -> dict:
    for a in list_attempts():
        if a["attempt_id"] == attempt_id:
            return a
    raise AttemptNotFoundError(f"Attempt '{attempt_id}' not found")


def _next_attempt_id(existing: List[dict]) -> str:
    max_n = 0
    for a in existing:
        aid = a.get("attempt_id", "")
        if aid.startswith("ATT-"):
            try:
                max_n = max(max_n, int(aid.split("-")[1]))
            except (IndexError, ValueError):
                continue
    return f"ATT-{max_n + 1:04d}"


def _write_all(rows: List[dict]) -> None:
    with open(ATTEMPTS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})


def start_attempt(case_id: str, student_name: str) -> dict:
    """Record that a student opened a case. If the student already has
    an IN_PROGRESS attempt on this exact case, that existing attempt is
    returned unchanged rather than creating a duplicate - re-opening a
    case you haven't finished yet shouldn't inflate the attempt count."""
    with _write_lock:
        existing = list_attempts()
        name = (student_name or "Anonymous").strip() or "Anonymous"

        for a in existing:
            if (
                a.get("case_id") == case_id
                and a.get("student_name", "").strip().lower() == name.lower()
                and a.get("status") == "IN_PROGRESS"
            ):
                return a

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_attempt = {k: "" for k in FIELDS}
        new_attempt.update(
            {
                "attempt_id": _next_attempt_id(existing),
                "case_id": case_id,
                "student_name": name,
                "status": "IN_PROGRESS",
                "started_at": now,
                "completed_at": "",
            }
        )
        _write_all(existing + [new_attempt])
        return new_attempt


def complete_attempt(
    attempt_id: str,
    student_root_cause: str = "",
    student_osi_layer: str = "",
    student_next_command: str = "",
    student_fix: str = "",
    ai_root_cause: str = "",
    matches_expected_concept: Optional[bool] = None,
) -> dict:
    """Mark an attempt COMPLETED. The student_*/ai_root_cause/
    matches_expected_concept fields are optional - plain Student
    Workspace usage (no Practice Mode) completes an attempt with none
    of them set; Practice Mode (practice.py) fills them in."""
    with _write_lock:
        existing = list_attempts()
        found = False
        updated_rows = []
        for a in existing:
            if a["attempt_id"] == attempt_id:
                found = True
                updated = dict(a)
                updated["status"] = "COMPLETED"
                updated["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if student_root_cause:
                    updated["student_root_cause"] = student_root_cause
                if student_osi_layer:
                    updated["student_osi_layer"] = student_osi_layer
                if student_next_command:
                    updated["student_next_command"] = student_next_command
                if student_fix:
                    updated["student_fix"] = student_fix
                if ai_root_cause:
                    updated["ai_root_cause"] = ai_root_cause
                if matches_expected_concept is not None:
                    updated["matches_expected_concept"] = str(matches_expected_concept)
                updated_rows.append(updated)
            else:
                updated_rows.append(a)

        if not found:
            raise AttemptNotFoundError(f"Attempt '{attempt_id}' not found")

        _write_all(updated_rows)
        return next(r for r in updated_rows if r["attempt_id"] == attempt_id)


def student_summary(student_name: str) -> dict:
    """Counts used by the Student Workspace dashboard: attempted
    (any attempt exists) and completed, per-concept breakdown, plus
    which case_ids fall into each bucket so the UI can badge them."""
    attempts = list_attempts_for_student(student_name)

    attempted_case_ids = {a["case_id"] for a in attempts}
    completed_case_ids = {a["case_id"] for a in attempts if a["status"] == "COMPLETED"}
    in_progress_case_ids = attempted_case_ids - completed_case_ids

    return {
        "attempted_case_ids": sorted(attempted_case_ids),
        "completed_case_ids": sorted(completed_case_ids),
        "in_progress_case_ids": sorted(in_progress_case_ids),
        "attempted_count": len(attempted_case_ids),
        "completed_count": len(completed_case_ids),
    }

def all_students_progress_summary() -> List[dict]:
    """Gather attempts across all students, aggregated by case_id for the admin dashboard."""
    attempts = list_attempts()
    stats_by_case = {}
    
    for a in attempts:
        cid = a.get("case_id")
        if not cid: continue
        if cid not in stats_by_case:
            stats_by_case[cid] = {"case_id": cid, "total_attempts": 0, "completed": 0, "successful": 0}
        
        stats_by_case[cid]["total_attempts"] += 1
        if a.get("status") == "COMPLETED":
            stats_by_case[cid]["completed"] += 1
            if a.get("matches_expected_concept") == "True":
                stats_by_case[cid]["successful"] += 1
                
    # Calculate success rates
    result = []
    for stats in stats_by_case.values():
        total = stats["total_attempts"]
        success_rate = (stats["successful"] / total * 100) if total > 0 else 0
        stats["success_rate_percent"] = round(success_rate, 1)
        result.append(stats)
        
    return result
