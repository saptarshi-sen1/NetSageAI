"""
One-time migration: adds case-management columns to data/cases.csv so
the app can support user-created cases alongside the original 30 seed
cases, without altering any existing row's troubleshooting content.

New columns (all additive):
    status      - "active" | "archived"
    source      - "seed" | "user"
    created_at  - ISO 8601 UTC timestamp
    updated_at  - ISO 8601 UTC timestamp
    created_by  - free-text author name

Safe to re-run: if the CSV already has these columns, it's left
untouched (idempotent).

Run: python3 migrate_cases_schema.py
"""
import csv
import os
from datetime import datetime, timezone

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CASES_CSV = os.path.join(_THIS_DIR, "cases.csv")

NEW_FIELDS = ["status", "source", "created_at", "updated_at", "created_by"]
SEED_TIMESTAMP = "2026-06-01T00:00:00Z"


def main():
    with open(CASES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if all(col in fieldnames for col in NEW_FIELDS):
        print("cases.csv already has case-management columns - nothing to do.")
        return

    updated_fieldnames = list(fieldnames) + [c for c in NEW_FIELDS if c not in fieldnames]

    for row in rows:
        row.setdefault("status", "active")
        row.setdefault("source", "seed")
        row.setdefault("created_at", SEED_TIMESTAMP)
        row.setdefault("updated_at", SEED_TIMESTAMP)
        row.setdefault("created_by", "NetSage AI Course Dataset")

    with open(CASES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=updated_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Migrated {len(rows)} cases with new columns: {NEW_FIELDS}")


if __name__ == "__main__":
    main()
