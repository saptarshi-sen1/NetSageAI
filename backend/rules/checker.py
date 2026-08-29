"""
NetSage AI - Deterministic Rule Checker

This module aggregates every check in backend/rules/*.py and runs them
against a case's evidence text. It is intentionally LLM-free: same
input always produces the same output. This is the "deterministic
findings" layer that the AI diagnosis is displayed alongside (never
merged into) so a human reviewer can compare the two independently.

CLI usage (from the project root or from backend/rules/):
    python checker.py                 # run against every case in data/cases.csv
    python checker.py --case VLAN-001  # run against a single case
    python checker.py --json           # machine-readable output
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import List

# Allow running this file directly (`python checker.py`) as well as as
# part of the package (`python -m backend.rules.checker`).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.rules import (
    acl_checks,
    dhcp_checks,
    ip_checks,
    nat_checks,
    routing_checks,
    security_checks,
    vlan_checks,
)
from backend.rules.models import Finding

DATA_CASES_CSV = os.path.join(_PROJECT_ROOT, "data", "cases.csv")

# Every deterministic check function to run, in a stable order so output
# is reproducible. Each takes the combined evidence text and returns a
# List[Finding] (possibly empty).
CHECK_FUNCTIONS = [
    ip_checks.check_duplicate_ip,
    ip_checks.check_wrong_subnet_mask,
    ip_checks.check_gateway_mismatch,
    ip_checks.check_interface_down,
    vlan_checks.check_missing_vlan,
    vlan_checks.check_access_port_vlan_assignment,
    vlan_checks.check_trunk_configuration,
    vlan_checks.check_native_vlan_mismatch,
    routing_checks.check_missing_default_route,
    routing_checks.check_missing_route,
    dhcp_checks.check_dhcp_pool_missing,
    dhcp_checks.check_dhcp_excluded_range,
    nat_checks.check_nat_inside_outside,
    nat_checks.check_nat_overload,
    acl_checks.check_acl_deny_statements,
    acl_checks.check_acl_applied_to_management,
    security_checks.check_port_security_violation,
]


def build_evidence_text(case: dict) -> str:
    """Combine the fields a deterministic checker is allowed to see.
    Deliberately excludes expected_fault/expected_evidence/expected_fix -
    those are ground truth used only for offline accuracy comparison,
    never fed into the checker or the AI."""
    parts = [
        case.get("topology_note", ""),
        case.get("symptom", ""),
        case.get("show_outputs", ""),
    ]
    return "\n".join(p for p in parts if p)


def run_checks(case: dict) -> List[Finding]:
    """Run every deterministic check against a single case dict (as
    loaded from data/cases.csv) and return the combined findings list."""
    text = build_evidence_text(case)
    findings: List[Finding] = []
    for check_fn in CHECK_FUNCTIONS:
        try:
            result = check_fn(text)
        except Exception as exc:  # a check must never crash the app
            findings.append(
                Finding(
                    rule=getattr(check_fn, "__name__", "unknown_check"),
                    status="WARN",
                    severity="LOW",
                    evidence="",
                    message=f"Check raised an internal error and was skipped: {exc}",
                )
            )
            continue
        findings.extend(result)
    return findings


def load_cases(path: str = DATA_CASES_CSV) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_case(case_id: str, path: str = DATA_CASES_CSV) -> dict | None:
    for case in load_cases(path):
        if case["case_id"] == case_id:
            return case
    return None


def _print_human(case_id: str, findings: List[Finding]) -> None:
    print(f"\n=== {case_id} ===")
    if not findings:
        print("  No deterministic findings.")
        return
    for f in findings:
        print(f"  [{f.status:4s}] [{f.severity:8s}] {f.rule}")
        print(f"           evidence: {f.evidence}")
        print(f"           message:  {f.message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="NetSage AI deterministic rule checker")
    parser.add_argument("--case", help="Run against a single case_id (default: all cases)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    if args.case:
        case = load_case(args.case)
        if not case:
            print(f"Case '{args.case}' not found in {DATA_CASES_CSV}", file=sys.stderr)
            sys.exit(1)
        cases = [case]
    else:
        cases = load_cases()

    results = {}
    for case in cases:
        findings = run_checks(case)
        results[case["case_id"]] = [f.to_dict() for f in findings]
        if not args.json:
            _print_human(case["case_id"], findings)

    if args.json:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
