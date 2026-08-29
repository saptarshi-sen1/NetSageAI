"""
Deterministic routing checks. Pure string/regex parsing - no LLM.
"""
from __future__ import annotations

import ipaddress
import re
from typing import List

from backend.rules.models import Finding

CIDR_RE = r"\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}"


def _normalize_cidrs(cidrs: set[str]) -> set[str]:
    """Normalize a set of CIDR strings to their network address so that
    e.g. '192.168.100.2/30' (a host address) and '192.168.100.0/30' (the
    network address, as printed in a routing table) are recognized as
    the same network rather than a false-positive mismatch."""
    normalized = set()
    for cidr in cidrs:
        try:
            normalized.add(str(ipaddress.ip_network(cidr, strict=False)))
        except ValueError:
            continue
    return normalized

# Matches a "show ip route ..." block up to (but not including) the next
# device-prompt line (e.g. "\nR1# ping ...") or end of string. Handles
# Cisco's habit of inserting a blank line between "Gateway of last
# resort..." and the actual route entries.
ROUTE_SECTION_RE = re.compile(r"show ip route\b.*?(?=\n\S+[#>]\s|\Z)", re.S)


def check_missing_default_route(text: str) -> List[Finding]:
    """Flag a router that explicitly reports no gateway of last resort."""
    findings: List[Finding] = []
    if re.search(r"Gateway of last resort is not set", text):
        has_default_route_line = re.search(r"0\.0\.0\.0/0", text) or re.search(
            r"ip route 0\.0\.0\.0 0\.0\.0\.0", text
        )
        if not has_default_route_line:
            findings.append(
                Finding(
                    rule="missing_default_route",
                    status="FAIL",
                    severity="CRITICAL",
                    evidence="show ip route reports: 'Gateway of last resort is not set'",
                    message=(
                        "No default route (0.0.0.0/0) is configured, so traffic "
                        "to any network not explicitly known cannot be routed."
                    ),
                )
            )
    return findings


def check_missing_route(text: str) -> List[Finding]:
    """Flags networks that are referenced as destinations in the case but
    never appear inside any 'show ip route' section of the evidence.

    Two signals are used, both deterministic:
      1. An explicit "(no route to ... 10.10.30.0/24)" style annotation
         in the supplied show output, if present.
      2. A network mentioned elsewhere in the case (typically the
         topology note, describing a remote LAN) that is absent from
         every captured routing-table section.
    Only runs when at least one 'show ip route' section is present, to
    avoid false positives on cases with no routing evidence at all.
    """
    findings: List[Finding] = []

    if "show ip route" not in text:
        return findings

    # Signal 1: explicit "no route to X" annotations, captured before we
    # strip them out (so they don't get miscounted as "present").
    annotation_hits = set(
        re.findall(r"no route to[^)\n]*?(" + CIDR_RE + r")", text, re.I)
    )
    stripped_text = re.sub(r"\(no route to[^)]*\)", "", text)

    # Signal 2: diff of all CIDRs mentioned anywhere vs. CIDRs that
    # actually appear inside a captured routing-table section.
    route_sections = ROUTE_SECTION_RE.findall(stripped_text)
    route_table_text = "\n".join(route_sections)
    route_table_cidrs = _normalize_cidrs(set(re.findall(CIDR_RE, route_table_text)))
    narrative_cidrs_raw = set(re.findall(CIDR_RE, stripped_text))
    narrative_cidrs = _normalize_cidrs(narrative_cidrs_raw)

    missing = annotation_hits | (narrative_cidrs - route_table_cidrs)

    for net in sorted(missing):
        prefix_len = int(net.split("/")[1])
        # Point-to-point transit links (/30, /31) are lower-severity if
        # missing, since they're less often the actual destination in
        # question versus a full LAN prefix.
        severity = "HIGH" if prefix_len <= 24 else "MEDIUM"
        findings.append(
            Finding(
                rule="missing_route",
                status="FAIL",
                severity=severity,
                evidence=f"{net} is referenced in the case but absent from every captured routing-table section",
                message=(
                    f"{net} does not appear in show ip route, which is "
                    "consistent with a missing static or dynamic route to "
                    "that destination."
                ),
            )
        )
    return findings
