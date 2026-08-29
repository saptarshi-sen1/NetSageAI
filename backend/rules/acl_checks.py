"""
Deterministic ACL checks. Pure string/regex parsing - no LLM.

Note: the presence of a 'deny' line in an ACL is not automatically a
fault - ACLs are often deliberately restrictive. This checker's job is
only to surface deny statements as structured findings so a human (or
the AI, as a secondary opinion) can judge whether a given deny line
explains the reported symptom.
"""
from __future__ import annotations

import re
from typing import List

from backend.rules.models import Finding


def check_acl_deny_statements(text: str) -> List[Finding]:
    findings: List[Finding] = []

    # Standard ACLs: "    10 deny   10.10.1.0 0.0.0.255"
    standard_denies = re.findall(
        r"^\s*\d+\s+deny\s+(\S.*)$", text, re.M
    )
    for entry in standard_denies:
        findings.append(
            Finding(
                rule="acl_deny_statement",
                status="WARN",
                severity="MEDIUM",
                evidence=f"deny {entry.strip()}",
                message=(
                    "This access list contains a deny statement. Confirm "
                    "whether it is intentionally blocking the traffic in "
                    "question or is the cause of the reported symptom."
                ),
            )
        )

    return findings


def check_acl_applied_to_management(text: str) -> List[Finding]:
    """Flag when an ACL with a deny statement is applied inbound to VTY
    (SSH/Telnet management) lines - a common way admins accidentally
    lock themselves out."""
    findings: List[Finding] = []

    vty_acl = re.search(r"access-class\s+(\S+)\s+in", text)
    if not vty_acl:
        return findings

    acl_name = vty_acl.group(1)
    acl_block_match = re.search(
        rf"(?:Standard|Extended) IP access list {re.escape(acl_name)}\n((?:.*\n)*?)(?:\n|\Z)",
        text,
    )
    if not acl_block_match:
        return findings

    acl_block = acl_block_match.group(1)
    if "deny" in acl_block:
        findings.append(
            Finding(
                rule="acl_blocks_management_access",
                status="WARN",
                severity="HIGH",
                evidence=(
                    f"access-class {acl_name} in is applied to the VTY lines, "
                    f"and {acl_name} contains at least one deny statement"
                ),
                message=(
                    f"ACL {acl_name} is applied to VTY (SSH/Telnet) access and "
                    "contains a deny entry - check its permit/deny order "
                    "carefully, since a misordered ACL here can lock "
                    "administrators out of remote management."
                ),
            )
        )
    return findings
