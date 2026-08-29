"""
One-time migration: adds verification-workflow columns to
data/reviews.csv, so the reviewer can mark a fix Verified / Verification
Failed / Not Yet Verified as a distinct stage after Accept/Edit/Reject,
and so corrected cases can record what evidence the AI missed.

New columns (all additive):
    verification_status  - "NOT_VERIFIED" | "VERIFIED" | "VERIFICATION_FAILED"
    evidence_missed       - free-text, only meaningful for EDITED/REJECTED reviews

Safe to re-run (idempotent).

Run: python3 migrate_reviews_schema.py
"""
import csv
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REVIEWS_CSV = os.path.join(_THIS_DIR, "reviews.csv")

NEW_FIELDS = ["verification_status", "evidence_missed"]


def main():
    if not os.path.exists(REVIEWS_CSV):
        print("reviews.csv does not exist - nothing to migrate.")
        return

    with open(REVIEWS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if all(col in fieldnames for col in NEW_FIELDS):
        print("reviews.csv already has verification columns - nothing to do.")
        return

    updated_fieldnames = list(fieldnames) + [c for c in NEW_FIELDS if c not in fieldnames]

    for row in rows:
        row.setdefault("verification_status", "NOT_VERIFIED")
        row.setdefault("evidence_missed", "")

    with open(REVIEWS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=updated_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Migrated {len(rows)} reviews with new columns: {NEW_FIELDS}")


if __name__ == "__main__":
    main()
