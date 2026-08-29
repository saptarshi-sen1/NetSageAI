"""
Deterministic DHCP checks. Pure string/regex parsing - no LLM.
"""
from __future__ import annotations

import ipaddress
import re
from typing import List

from backend.rules.models import Finding


def check_dhcp_pool_missing(text: str) -> List[Finding]:
    """Flag a router configured as a DHCP server with no pool defined."""
    findings: List[Finding] = []
    if re.search(r"%\s*No DHCP pools configured", text):
        findings.append(
            Finding(
                rule="dhcp_pool_missing",
                status="FAIL",
                severity="CRITICAL",
                evidence="show ip dhcp pool reports: '% No DHCP pools configured'",
                message=(
                    "No DHCP pool is configured on this router, so clients "
                    "cannot lease an address and will fall back to an APIPA "
                    "(169.254.x.x) address."
                ),
            )
        )
    return findings


def check_dhcp_excluded_range(text: str) -> List[Finding]:
    """Flag an excluded-address range that removes most of the pool's
    usable addresses, based on the network size declared in the same
    pool."""
    findings: List[Finding] = []

    excl = re.search(
        r"ip dhcp excluded-address\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})",
        text,
    )
    # Supports both the running-config style ("network A.B.C.D M.M.M.M")
    # and the "show ip dhcp pool" style ("Network: A.B.C.D/NN").
    net_match_config = re.search(
        r"network\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})", text
    )
    net_match_show = re.search(
        r"Network:\s*(\d{1,3}(?:\.\d{1,3}){3})/(\d{1,2})", text
    )
    if not excl or not (net_match_config or net_match_show):
        return findings

    start_ip, end_ip = excl.groups()

    try:
        if net_match_config:
            net_addr, net_mask = net_match_config.groups()
            network = ipaddress.ip_network(f"{net_addr}/{net_mask}", strict=False)
        else:
            net_addr, prefix_len = net_match_show.groups()
            network = ipaddress.ip_network(f"{net_addr}/{prefix_len}", strict=False)
        excluded_count = int(ipaddress.ip_address(end_ip)) - int(
            ipaddress.ip_address(start_ip)
        ) + 1
        usable = network.num_addresses - 2  # network + broadcast
        if usable <= 0:
            return findings
        excluded_ratio = excluded_count / usable
    except ValueError:
        return findings

    if excluded_ratio >= 0.8:
        findings.append(
            Finding(
                rule="dhcp_excluded_range",
                status="FAIL",
                severity="HIGH",
                evidence=(
                    f"ip dhcp excluded-address {start_ip} {end_ip} removes "
                    f"~{excluded_count} of {usable} usable addresses "
                    f"({excluded_ratio:.0%}) from pool {network}"
                ),
                message=(
                    "The excluded-address range removes the large majority "
                    "of the usable address space from this DHCP pool, which "
                    "will exhaust available leases quickly."
                ),
            )
        )
    return findings
