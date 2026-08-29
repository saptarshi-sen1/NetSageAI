"""
Deterministic Layer 1-3 addressing checks.

Every function takes the combined case text (topology note + symptom +
show-command output) and returns a list of Finding objects. No network
calls, no LLM calls - pure string/regex parsing so results are
reproducible.
"""
from __future__ import annotations

import re
from typing import List

from backend.rules.models import Finding

IP_RE = r"\d{1,3}(?:\.\d{1,3}){3}"


def check_duplicate_ip(text: str) -> List[Finding]:
    """Flag an IP address that appears bound to more than one MAC address
    in an ARP table (`show ip arp`)."""
    findings: List[Finding] = []

    arp_rows = re.findall(
        rf"Internet\s+({IP_RE})\s+\S+\s+([0-9A-Fa-f]{{4}}\.[0-9A-Fa-f]{{4}}\.[0-9A-Fa-f]{{4}})",
        text,
    )
    if not arp_rows:
        return findings

    ip_to_macs: dict[str, set[str]] = {}
    for ip, mac in arp_rows:
        ip_to_macs.setdefault(ip, set()).add(mac.lower())

    for ip, macs in ip_to_macs.items():
        if len(macs) > 1:
            findings.append(
                Finding(
                    rule="duplicate_ip",
                    status="FAIL",
                    severity="MEDIUM",
                    evidence=f"{ip} is mapped to multiple MAC addresses: {', '.join(sorted(macs))}",
                    message=(
                        f"Address {ip} appears bound to {len(macs)} different MAC "
                        "addresses in the ARP table, which indicates a duplicate "
                        "IP address conflict."
                    ),
                )
            )
    return findings


def check_wrong_subnet_mask(text: str) -> List[Finding]:
    """Flag a case where multiple host `ipconfig` blocks on the same
    apparent subnet report different subnet masks."""
    findings: List[Finding] = []

    blocks = re.findall(
        rf"IP Address\.*:\s*({IP_RE}).*?Subnet Mask\.*:\s*({IP_RE})",
        text,
        re.S,
    )
    if len(blocks) < 2:
        return findings

    masks = {mask for _, mask in blocks}
    if len(masks) > 1:
        detail = ", ".join(f"{ip} -> {mask}" for ip, mask in blocks)
        findings.append(
            Finding(
                rule="wrong_subnet_mask",
                status="FAIL",
                severity="MEDIUM",
                evidence=detail,
                message=(
                    "Hosts on what appears to be the same subnet report "
                    f"inconsistent subnet masks: {', '.join(sorted(masks))}."
                ),
            )
        )
    return findings


def check_gateway_mismatch(text: str) -> List[Finding]:
    """Flag a host whose configured default gateway is blank, or whose
    gateway IP never appears as a configured interface address anywhere
    else in the supplied evidence."""
    findings: List[Finding] = []

    gw_blocks = re.findall(rf"Default Gateway\.*:\s*({IP_RE})?\s*\n", text)
    if not gw_blocks:
        return findings

    # All IP addresses assigned to router/switch interfaces mentioned
    # anywhere in the evidence (from "show ip interface brief" style output).
    iface_ips = set(
        re.findall(
            rf"(?:GigabitEthernet|FastEthernet|Serial|Vlan|Loopback)\S*\s+({IP_RE})",
            text,
        )
    )

    for gw in gw_blocks:
        if gw == "" or gw is None:
            findings.append(
                Finding(
                    rule="gateway_mismatch",
                    status="FAIL",
                    severity="HIGH",
                    evidence="Default Gateway field is blank in ipconfig output",
                    message=(
                        "A host has no default gateway configured, so it cannot "
                        "route traffic to any network outside its local subnet."
                    ),
                )
            )
        elif iface_ips and gw not in iface_ips:
            findings.append(
                Finding(
                    rule="gateway_mismatch",
                    status="FAIL",
                    severity="HIGH",
                    evidence=(
                        f"Host default gateway is {gw}, but the only interface "
                        f"addresses found in the evidence are: {', '.join(sorted(iface_ips))}"
                    ),
                    message=(
                        f"The host's configured gateway {gw} does not match any "
                        "router/switch interface address present in the supplied "
                        "evidence, suggesting the gateway is pointed at a "
                        "non-existent or incorrect address."
                    ),
                )
            )
    return findings


def check_interface_down(text: str) -> List[Finding]:
    """Flag interfaces reported as administratively down or with a down
    line protocol."""
    findings: List[Finding] = []

    admin_down = re.findall(
        r"(\S+(?:Ethernet|Serial|Vlan|Dot11Radio)\S*)\s+\S+\s+YES\s+\S+\s+administratively down",
        text,
    )
    for iface in admin_down:
        findings.append(
            Finding(
                rule="interface_down",
                status="FAIL",
                severity="HIGH",
                evidence=f"{iface} status: administratively down",
                message=(
                    f"Interface {iface} is administratively down (shut down in "
                    "configuration) and will not pass any traffic until it is "
                    "brought up."
                ),
            )
        )

    # Radio / physical interfaces reported down outside the ip-int-brief table
    radio_down = re.findall(
        r"(Dot11Radio\d+) is administratively down, line protocol is down",
        text,
    )
    for iface in radio_down:
        findings.append(
            Finding(
                rule="interface_down",
                status="FAIL",
                severity="CRITICAL",
                evidence=f"{iface} is administratively down, line protocol is down",
                message=(
                    f"Radio interface {iface} is administratively down, so the "
                    "access point is not transmitting at all."
                ),
            )
        )

    return findings
