"""
Case service - reads and writes data/cases.csv.

Originally this file was read-only ("the dataset is a fixed course
artifact"). It now also supports case management (create / update /
archive / restore) so instructors or students can add their own
troubleshooting cases through the exact same Case -> Rule Checker ->
AI Diagnosis -> Human Review -> Verification workflow the 30 seed
cases already use - no separate code path, no separate storage.

Backward compatibility note: list_cases() keeps working with ZERO
arguments exactly as before (every existing call site - api/cases.py,
api/dashboard.py - calls it with no args and gets active cases back,
which was already the only kind of case that existed). New optional
filter/search parameters are additive only.

Design choices carried over from review_service.py:
  - CSV, not a database - consistent with the rest of the project and
    the "no unnecessary enterprise architecture" instruction.
  - mtime-based caching so list_cases() stays cheap under repeated
    requests but still picks up writes immediately (the cache key is
    the file's own mtime, which changes on every write this module makes).
  - A single write lock so create/update/archive don't interleave and
    corrupt the CSV under concurrent requests from the simple dev
    server this project targets.

New concept: every case has `status` ("active" | "archived") and
`source` ("seed" | "user"). Archiving is a soft delete - archived cases
are excluded from list_cases() by default but never physically
removed, so review history (data/reviews.csv) referencing an archived
case_id still resolves via get_case().
"""
from __future__ import annotations

import csv
import os
import threading
from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Optional

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
CASES_CSV_PATH = os.path.join(PROJECT_ROOT, "data", "cases.csv")

# Full column set written to disk. Older/pre-migration CSVs are read
# fine too - see _load_all_cases_cached()'s setdefault() calls below.
FIELDS = [
    "case_id", "title", "symptom", "topology_note", "show_outputs",
    "expected_fault", "osi_layer", "concept", "severity",
    "expected_evidence", "expected_next_command", "expected_fix",
    "verification_command", "difficulty",
    "status", "source", "created_at", "updated_at", "created_by",
]

# The subset of fields a case-creation/edit form actually submits.
# case_id/status/source/timestamps are always assigned by this module,
# never accepted from the caller directly.
EDITABLE_FIELDS = [
    "title", "symptom", "topology_note", "show_outputs",
    "expected_fault", "osi_layer", "concept", "severity",
    "expected_evidence", "expected_next_command", "expected_fix",
    "verification_command", "difficulty",
]

_write_lock = threading.Lock()


class CaseNotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_all_cases_cached(mtime: float) -> tuple:
    """Cached on the file's mtime, so editing data/cases.csv (by hand
    during a dev session, or through this module's own write functions
    below) picks up changes immediately, while repeated requests in
    between don't re-read the file."""
    with open(CASES_CSV_PATH, newline="", encoding="utf-8") as f:
        rows = []
        for row in csv.DictReader(f):
            row = dict(row)
            # Backward compatible with a pre-migration CSV missing the
            # newer management columns - every row gets sane defaults
            # rather than the app crashing on a KeyError.
            row.setdefault("status", "active")
            row.setdefault("source", "seed")
            row.setdefault("created_at", "")
            row.setdefault("updated_at", "")
            row.setdefault("created_by", "")
            rows.append(row)
        return tuple(rows)


def _load_all_cases_raw() -> List[dict]:
    """Every case regardless of status - internal helper for the write
    functions below, which need to see archived rows too so they don't
    get dropped on a rewrite."""
    mtime = os.path.getmtime(CASES_CSV_PATH)
    return list(_load_all_cases_cached(mtime))


def list_cases(
    include_archived: bool = False,
    concept: Optional[str] = None,
    severity: Optional[str] = None,
    osi_layer: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
) -> List[dict]:
    """List cases, active-only by default (unchanged behavior from
    before this module supported archiving - every pre-existing caller
    that invokes list_cases() with no arguments gets exactly the same
    result shape as always). Optional filters combine with AND and are
    all additive/backward-compatible."""
    cases = _load_all_cases_raw()

    if not include_archived:
        cases = [c for c in cases if c.get("status", "active") != "archived"]
    if concept:
        cases = [c for c in cases if c.get("concept") == concept]
    if severity:
        cases = [c for c in cases if c.get("severity") == severity]
    if osi_layer:
        cases = [c for c in cases if c.get("osi_layer") == osi_layer]
    if difficulty:
        cases = [c for c in cases if c.get("difficulty") == difficulty]
    if search:
        q = search.strip().lower()
        cases = [
            c
            for c in cases
            if q in c.get("case_id", "").lower()
            or q in c.get("title", "").lower()
            or q in c.get("symptom", "").lower()
        ]
    return cases


def get_case(case_id: str) -> dict:
    """Looks up a case by id REGARDLESS of archived status, exactly
    like before (the original implementation had no concept of
    archiving, so every case was always "findable"). This matters so
    that review history pointing at an archived case_id still resolves
    instead of 404ing."""
    for case in _load_all_cases_raw():
        if case["case_id"] == case_id:
            return case
    raise CaseNotFoundError(f"Case '{case_id}' not found")


def get_case_or_none(case_id: str) -> Optional[dict]:
    try:
        return get_case(case_id)
    except CaseNotFoundError:
        return None


def summary_counts(include_archived: bool = False) -> dict:
    cases = list_cases(include_archived=include_archived)
    by_concept: dict = {}
    by_severity: dict = {}
    by_osi_layer: dict = {}
    for c in cases:
        by_concept[c["concept"]] = by_concept.get(c["concept"], 0) + 1
        by_severity[c["severity"]] = by_severity.get(c["severity"], 0) + 1
        by_osi_layer[c["osi_layer"]] = by_osi_layer.get(c["osi_layer"], 0) + 1
    return {
        "total_cases": len(cases),
        "by_concept": by_concept,
        "by_severity": by_severity,
        "by_osi_layer": by_osi_layer,
    }


def distinct_facet_values() -> dict:
    """Distinct concept/severity/osi_layer/difficulty values across all
    active cases, so the frontend can populate filter dropdowns without
    deriving them client-side from a full case list."""
    cases = list_cases(include_archived=False)
    return {
        "concepts": sorted({c["concept"] for c in cases if c.get("concept")}),
        "severities": sorted({c["severity"] for c in cases if c.get("severity")}),
        "osi_layers": sorted({c["osi_layer"] for c in cases if c.get("osi_layer")}),
        "difficulties": sorted({c["difficulty"] for c in cases if c.get("difficulty")}),
    }


# ---------------------------------------------------------------------------
# Writing (create / update / archive / restore)
# ---------------------------------------------------------------------------
def _write_all(cases: List[dict]) -> None:
    with open(CASES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in cases:
            writer.writerow({k: row.get(k, "") for k in FIELDS})
    # Explicit cache invalidation is needed on Windows: NTFS mtime
    # granularity can be ~1-2 seconds, so two writes within the same
    # second produce identical mtime values and the LRU cache returns
    # stale data. Clearing unconditionally is cheap and cross-platform.
    _load_all_cases_cached.cache_clear()


def _next_user_case_id(existing: List[dict]) -> str:
    """User-created cases get a distinct CASE-XXXX id, visually
    different from the seed dataset's topic-prefixed ids (VLAN-001,
    DHCP-001, etc.) so it's always obvious which cases are original
    course material versus instructor/student-added."""
    max_n = 0
    for c in existing:
        cid = c.get("case_id", "")
        if cid.startswith("CASE-"):
            try:
                max_n = max(max_n, int(cid.split("-")[1]))
            except (IndexError, ValueError):
                continue
    return f"CASE-{max_n + 1:04d}"


def create_case(fields: dict, created_by: str = "Anonymous") -> dict:
    """Create a new case. `fields` should contain the EDITABLE_FIELDS
    keys (missing ones default to ""); case_id/status/source/timestamps
    are assigned here, never accepted from the caller. The new case is
    written to data/cases.csv and is immediately visible to
    list_cases()/get_case() - it goes through the identical Case ->
    Rule Checker -> AI Diagnosis -> Human Review -> Verification
    pipeline as every seed case, since that pipeline only ever reads
    cases through get_case()."""
    with _write_lock:
        existing = _load_all_cases_raw()
        case_id = _next_user_case_id(existing)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        new_case = {k: str(fields.get(k, "") or "").strip() for k in EDITABLE_FIELDS}
        new_case.update(
            {
                "case_id": case_id,
                "status": "active",
                "source": "user",
                "created_at": now,
                "updated_at": now,
                "created_by": created_by or "Anonymous",
            }
        )

        _write_all(existing + [new_case])
        return new_case


def update_case(case_id: str, fields: dict) -> dict:
    """Update an existing case's editable fields (title, symptom,
    topology, evidence, etc). Never changes case_id, status, source, or
    created_at/created_by. Works for both seed and user-created cases -
    an instructor correcting a seed case's wording is a normal use case."""
    with _write_lock:
        existing = _load_all_cases_raw()
        found = False
        updated_rows = []
        for row in existing:
            if row["case_id"] == case_id:
                found = True
                updated = dict(row)
                for key in EDITABLE_FIELDS:
                    if key in fields and fields[key] is not None:
                        updated[key] = str(fields[key]).strip()
                updated["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                updated_rows.append(updated)
            else:
                updated_rows.append(row)

        if not found:
            raise CaseNotFoundError(f"Case '{case_id}' not found")

        _write_all(updated_rows)
        return next(r for r in updated_rows if r["case_id"] == case_id)


def set_case_status(case_id: str, status: str) -> dict:
    """Archive ("archived") or restore ("active") a case - a soft
    delete. See module docstring for why rows are never physically
    removed."""
    if status not in ("active", "archived"):
        raise ValueError("status must be 'active' or 'archived'")

    with _write_lock:
        existing = _load_all_cases_raw()
        found = False
        updated_rows = []
        for row in existing:
            if row["case_id"] == case_id:
                found = True
                updated = dict(row)
                updated["status"] = status
                updated["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                updated_rows.append(updated)
            else:
                updated_rows.append(row)

        if not found:
            raise CaseNotFoundError(f"Case '{case_id}' not found")

        _write_all(updated_rows)
        return next(r for r in updated_rows if r["case_id"] == case_id)
