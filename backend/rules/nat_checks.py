"""
Deterministic NAT checks. Pure string/regex parsing - no LLM.
"""
from __future__ import annotations

import re
from typing import List

from backend.rules.models import Finding


def check_nat_inside_outside(text: str) -> List[Finding]:
    """Flag a NAT configuration that defines translation rules but never
    marks any interface as 'ip nat inside' / 'ip nat outside'."""
    findings: List[Finding] = []

    has_nat_rule = re.search(r"ip nat inside source", text)
    has_interface_config = re.search(r"interface (GigabitEthernet|FastEthernet)", text)
    if not has_nat_rule or not has_interface_config:
        # Without interface configuration in the evidence, we can't
        # conclude the marking is actually missing - just that it wasn't
        # shown, which isn't a deterministic finding either way.
        return findings

    # Look for the interface-level marking commands specifically (a line
    # containing only "ip nat inside"/"ip nat outside"), not the "ip nat
    # inside source ..." translation-rule statement, which contains the
    # same words but is a different command entirely.
    has_inside = re.search(r"(?m)^\s*ip nat inside\s*$", text)
    has_outside = re.search(r"(?m)^\s*ip nat outside\s*$", text)

    missing_sides = []
    if not has_inside:
        missing_sides.append("ip nat inside")
    if not has_outside:
        missing_sides.append("ip nat outside")

    if missing_sides:
        findings.append(
            Finding(
                rule="nat_inside_outside_missing",
                status="FAIL",
                severity="CRITICAL",
                evidence=(
                    "A NAT translation rule ('ip nat inside source ...') "
                    f"exists, but no interface has {' or '.join(missing_sides)} applied."
                ),
                message=(
                    "NAT rules and ACLs may be correctly defined, but without "
                    "marking the inside and outside interfaces the router will "
                    "never actually perform any translation."
                ),
            )
        )
    return findings


def check_nat_overload(text: str) -> List[Finding]:
    """Flag NAT configurations that cannot scale to more than one inside
    host at a time, in either of two forms:
      1. A dynamic ('list'/'pool' based) NAT statement missing the
         'overload' keyword.
      2. Only a static one-to-one translation exists, with no dynamic
         or overload rule at all to cover the rest of the inside hosts.
    """
    findings: List[Finding] = []

    nat_lines = [
        line.strip() for line in re.findall(r"ip nat inside source[^\n]*", text)
    ]
    if not nat_lines:
        return findings

    dynamic_lines = [line for line in nat_lines if "static" not in line]
    static_lines = [line for line in nat_lines if "static" in line]

    for line in dynamic_lines:
        if ("list" in line or "pool" in line) and "overload" not in line:
            findings.append(
                Finding(
                    rule="nat_overload_missing",
                    status="FAIL",
                    severity="HIGH",
                    evidence=line,
                    message=(
                        "This dynamic NAT statement has no 'overload' "
                        "keyword, so each public address can serve only "
                        "one inside host at a time instead of being "
                        "shared via port address translation (PAT)."
                    ),
                )
            )

    if static_lines and not dynamic_lines:
        findings.append(
            Finding(
                rule="nat_overload_missing",
                status="FAIL",
                severity="HIGH",
                evidence="; ".join(static_lines),
                message=(
                    "Only a static one-to-one NAT translation exists. There "
                    "is no dynamic 'ip nat inside source list ... overload' "
                    "rule, so any inside host other than the one statically "
                    "mapped cannot be translated to reach the internet."
                ),
            )
        )
    return findings
