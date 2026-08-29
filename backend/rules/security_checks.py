"""
Deterministic port-security checks. Pure string/regex parsing - no LLM.
"""
from __future__ import annotations

import re
from typing import List

from backend.rules.models import Finding


def check_port_security_violation(text: str) -> List[Finding]:
    """Flag a port that has been placed in Secure-shutdown (err-disabled)
    by a port-security violation."""
    findings: List[Finding] = []

    if re.search(r"Port Status\s*:\s*Secure-shutdown", text):
        violation_count = re.search(r"Security Violation Count\s*:\s*(\d+)", text)
        max_mac = re.search(r"Maximum MAC Addresses\s*:\s*(\d+)", text)
        detail = []
        if max_mac:
            detail.append(f"Maximum MAC Addresses: {max_mac.group(1)}")
        if violation_count:
            detail.append(f"Security Violation Count: {violation_count.group(1)}")
        findings.append(
            Finding(
                rule="port_security_violation",
                status="FAIL",
                severity="MEDIUM",
                evidence="Port Status: Secure-shutdown" + (
                    " (" + ", ".join(detail) + ")" if detail else ""
                ),
                message=(
                    "This port is err-disabled after a port-security "
                    "violation (an unauthorized or additional MAC address "
                    "was seen on a port with a limited MAC count). It will "
                    "not pass traffic again until manually re-enabled."
                ),
            )
        )
    return findings
