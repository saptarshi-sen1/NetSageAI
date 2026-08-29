"""
Deterministic Layer 2 / VLAN checks. Pure string and regex parsing -
no LLM involved. See backend/rules/models.py for the Finding schema.
"""
from __future__ import annotations

import re
from typing import List

from backend.rules.models import Finding


def check_missing_vlan(text: str) -> List[Finding]:
    """Flag a port whose configured access VLAN does not exist in
    `show vlan brief` output (shown as "(Inactive)" by Packet Tracer/IOS),
    or a VLAN number referenced elsewhere that never appears in the VLAN
    database at all."""
    findings: List[Finding] = []

    inactive = re.findall(r"Access Mode VLAN:\s*(\d+)\s*\(Inactive\)", text)
    for vlan_id in inactive:
        findings.append(
            Finding(
                rule="missing_vlan",
                status="FAIL",
                severity="HIGH",
                evidence=f"Access Mode VLAN: {vlan_id} (Inactive)",
                message=(
                    f"The port's access VLAN is set to {vlan_id}, but that VLAN "
                    "does not exist in the switch's VLAN database (shown as "
                    "Inactive), so the port cannot forward traffic."
                ),
            )
        )

    # Cross-check: any "Access Mode VLAN: N" entries whose VLAN never
    # appears as a row in a "show vlan brief" table included in the evidence.
    vlan_brief_ids = set(re.findall(r"^\s*(\d{1,4})\s+\S+\s+active", text, re.M))
    access_vlan_ids = set(re.findall(r"Access Mode VLAN:\s*(\d+)", text))
    if vlan_brief_ids:
        for vlan_id in access_vlan_ids - vlan_brief_ids:
            already_flagged = any(f.rule == "missing_vlan" for f in findings)
            if not already_flagged:
                findings.append(
                    Finding(
                        rule="missing_vlan",
                        status="FAIL",
                        severity="HIGH",
                        evidence=(
                            f"Access Mode VLAN: {vlan_id} on a port, but VLAN "
                            f"{vlan_id} does not appear as an active row in "
                            "show vlan brief"
                        ),
                        message=(
                            f"VLAN {vlan_id} is assigned to a port but was never "
                            "created on this switch."
                        ),
                    )
                )
    return findings


def check_access_port_vlan_assignment(text: str) -> List[Finding]:
    """Best-effort cross-check: if the case narrative states a device
    'should be on/in VLAN N', flag it if the actual switchport evidence
    shows a different access VLAN."""
    findings: List[Finding] = []

    expected = re.findall(r"should be (?:on|in)\s+(?:a\s+)?VLAN\s*(\d+)", text, re.I)
    actual = re.findall(r"Access Mode VLAN:\s*(\d+)", text)

    if expected and actual:
        for exp in expected:
            if exp not in actual:
                findings.append(
                    Finding(
                        rule="access_port_vlan_mismatch",
                        status="FAIL",
                        severity="HIGH",
                        evidence=(
                            f"Case notes state the device should be on VLAN {exp}; "
                            f"switchport evidence shows Access Mode VLAN: "
                            f"{', '.join(actual)}"
                        ),
                        message=(
                            f"The port's actual access VLAN ({', '.join(actual)}) "
                            f"does not match the VLAN ({exp}) the device is "
                            "expected to be on."
                        ),
                    )
                )
    return findings


def check_trunk_configuration(text: str) -> List[Finding]:
    """Flag a trunk link where one side is confirmed trunking and the
    other side is reported as a static access port, or where a
    'show interfaces trunk' returns no trunking ports at all alongside
    evidence that a peer switch is trunking."""
    findings: List[Finding] = []

    trunking_seen = "trunking" in text
    no_trunk_ports = re.search(
        r"\(no output - no trunking interfaces found\)", text
    )
    static_access_on_uplink = re.search(
        r"Administrative Mode:\s*static access\s*\n\s*Operational Mode:\s*static access",
        text,
    )

    if trunking_seen and (no_trunk_ports or static_access_on_uplink):
        evidence_bits = []
        if no_trunk_ports:
            evidence_bits.append("a 'show interfaces trunk' with no trunking ports")
        if static_access_on_uplink:
            evidence_bits.append("an interface reporting static access mode")
        findings.append(
            Finding(
                rule="trunk_configuration",
                status="FAIL",
                severity="HIGH",
                evidence=(
                    "One side of the link shows 'trunking' while the other "
                    "side shows " + " and ".join(evidence_bits)
                ),
                message=(
                    "The two ends of this link disagree on trunk mode - one "
                    "side is trunking and the other is configured as a static "
                    "access port, so VLANs cannot cross the link."
                ),
            )
        )
    return findings


def check_native_vlan_mismatch(text: str) -> List[Finding]:
    """Flag when more than one distinct native VLAN value is reported for
    what appears to be the same trunk.

    'show interfaces trunk' prints Native vlan as a table COLUMN, e.g.:
        Port     Mode  Encapsulation  Status     Native vlan
        Gi0/2    on    802.1q         trunking   1
    so the value to extract is the last field of each interface data
    row, not text immediately following the words "Native vlan" (that
    phrase only appears once, in the header)."""
    findings: List[Finding] = []

    native_vlans = re.findall(
        r"(?m)^(?:Gi|Fa|Te|Po)\S*\s+\S+\s+\S+\s+\S+\s+(\d+)\s*$", text
    )
    distinct = sorted(set(native_vlans))
    if len(distinct) > 1:
        findings.append(
            Finding(
                rule="native_vlan_mismatch",
                status="FAIL",
                severity="MEDIUM",
                evidence=f"Native VLAN values found on this trunk: {', '.join(distinct)}",
                message=(
                    "The two ends of a trunk report different native VLANs "
                    f"({', '.join(distinct)}). A native VLAN mismatch causes "
                    "untagged traffic to leak between VLANs and typically "
                    "triggers a CDP native VLAN mismatch warning."
                ),
            )
        )
    return findings
