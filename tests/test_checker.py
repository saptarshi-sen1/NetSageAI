"""
Tests for the deterministic rule checker. Every check is pure and
LLM-free, so these tests assert exact, reproducible findings on small
hand-crafted snippets, in addition to sanity checks against the full
dataset.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.rules import (
    acl_checks,
    dhcp_checks,
    ip_checks,
    nat_checks,
    routing_checks,
    security_checks,
    vlan_checks,
)
from backend.rules.checker import build_evidence_text, load_case, load_cases, run_checks


# --------------------------------------------------------------------------
# Duplicate IP
# --------------------------------------------------------------------------
def test_duplicate_ip_detected():
    text = (
        "show ip arp\n"
        "Internet  10.10.10.20        4   00E0.1234.ABCD  ARPA   GigabitEthernet0/0\n"
        "Internet  10.10.10.20        1   00E0.5678.EF01  ARPA   GigabitEthernet0/0\n"
    )
    findings = ip_checks.check_duplicate_ip(text)
    assert len(findings) == 1
    assert findings[0].rule == "duplicate_ip"
    assert findings[0].status == "FAIL"


def test_duplicate_ip_not_flagged_when_single_mac():
    text = (
        "Internet  10.10.10.20        4   00E0.1234.ABCD  ARPA   GigabitEthernet0/0\n"
    )
    findings = ip_checks.check_duplicate_ip(text)
    assert findings == []


# --------------------------------------------------------------------------
# Wrong subnet mask
# --------------------------------------------------------------------------
def test_wrong_subnet_mask_detected():
    text = (
        "IP Address..........: 192.168.5.40\n"
        "Subnet Mask..........: 255.255.255.192\n"
        "IP Address..........: 192.168.5.41\n"
        "Subnet Mask..........: 255.255.255.0\n"
    )
    findings = ip_checks.check_wrong_subnet_mask(text)
    assert len(findings) == 1
    assert findings[0].rule == "wrong_subnet_mask"


def test_matching_masks_not_flagged():
    text = (
        "IP Address..........: 192.168.5.40\n"
        "Subnet Mask..........: 255.255.255.0\n"
        "IP Address..........: 192.168.5.41\n"
        "Subnet Mask..........: 255.255.255.0\n"
    )
    assert ip_checks.check_wrong_subnet_mask(text) == []


# --------------------------------------------------------------------------
# Gateway mismatch
# --------------------------------------------------------------------------
def test_blank_gateway_detected():
    text = "Default Gateway......: \n"
    findings = ip_checks.check_gateway_mismatch(text)
    assert len(findings) == 1
    assert findings[0].rule == "gateway_mismatch"


def test_gateway_not_matching_known_interfaces_flagged():
    text = (
        "Default Gateway......: 10.10.20.100\n"
        "GigabitEthernet0/1.20  10.10.20.1      YES manual up        up\n"
    )
    findings = ip_checks.check_gateway_mismatch(text)
    assert len(findings) == 1
    assert "10.10.20.100" in findings[0].evidence


def test_gateway_matching_known_interface_not_flagged():
    text = (
        "Default Gateway......: 10.10.20.1\n"
        "GigabitEthernet0/1.20  10.10.20.1      YES manual up        up\n"
    )
    assert ip_checks.check_gateway_mismatch(text) == []


# --------------------------------------------------------------------------
# Interface down
# --------------------------------------------------------------------------
def test_interface_down_detected():
    text = (
        "GigabitEthernet0/0     192.168.50.1    YES manual administratively down   down\n"
    )
    findings = ip_checks.check_interface_down(text)
    assert len(findings) == 1
    assert findings[0].severity == "HIGH"


def test_radio_interface_down_detected():
    text = "Dot11Radio0 is administratively down, line protocol is down\n"
    findings = ip_checks.check_interface_down(text)
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"


def test_interface_up_not_flagged():
    text = "GigabitEthernet0/0     192.168.50.1    YES manual up   up\n"
    assert ip_checks.check_interface_down(text) == []


# --------------------------------------------------------------------------
# Missing VLAN
# --------------------------------------------------------------------------
def test_missing_vlan_inactive_detected():
    text = "Access Mode VLAN: 40 (Inactive)\n"
    findings = vlan_checks.check_missing_vlan(text)
    assert len(findings) == 1
    assert findings[0].rule == "missing_vlan"


def test_vlan_present_not_flagged():
    text = (
        "1    default                          active    Fa0/1, Fa0/2\n"
        "10   Sales                            active    Fa0/3, Fa0/4\n"
        "Access Mode VLAN: 10\n"
    )
    assert vlan_checks.check_missing_vlan(text) == []


# --------------------------------------------------------------------------
# Missing route
# --------------------------------------------------------------------------
def test_missing_route_detected():
    text = (
        "topology: HQR owns 172.16.5.0/24 on its LAN.\n"
        "BranchR# show ip route\n"
        "Gateway of last resort is not set\n\n"
        "     172.16.1.0/24 is directly connected, GigabitEthernet0/0\n\n"
        "BranchR# ping 172.16.5.10\n"
    )
    findings = routing_checks.check_missing_route(text)
    rules_hit = [f.rule for f in findings]
    assert "missing_route" in rules_hit
    net_evidence = [f for f in findings if f.rule == "missing_route"][0]
    assert "172.16.5.0/24" in net_evidence.evidence


def test_route_present_not_flagged_missing():
    text = (
        "topology: HQR owns 172.16.5.0/24 on its LAN.\n"
        "BranchR# show ip route\n"
        "     172.16.5.0/24 is directly connected, GigabitEthernet0/0\n\n"
        "BranchR# ping 172.16.5.10\n"
    )
    findings = routing_checks.check_missing_route(text)
    assert findings == []


def test_missing_route_skipped_without_route_table_evidence():
    text = "topology mentions 172.16.5.0/24 but no routing table is shown anywhere"
    assert routing_checks.check_missing_route(text) == []


def test_missing_default_route_detected():
    text = "Gateway of last resort is not set\n\n   10.0.0.0/8 is variably subnetted\n"
    findings = routing_checks.check_missing_default_route(text)
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"


def test_default_route_present_not_flagged():
    text = "Gateway of last resort is 203.0.113.1 to network 0.0.0.0/0\n"
    assert routing_checks.check_missing_default_route(text) == []


# --------------------------------------------------------------------------
# ACL
# --------------------------------------------------------------------------
def test_acl_deny_statement_surfaced():
    text = "    10 deny   10.10.1.0 0.0.0.255\n    20 permit any\n"
    findings = acl_checks.check_acl_deny_statements(text)
    assert len(findings) == 1
    assert findings[0].status == "WARN"


def test_acl_blocking_management_flagged():
    text = (
        "Standard IP access list MGMT-ACL\n"
        "    10 deny   10.10.1.0 0.0.0.255\n"
        "    20 permit any\n\n"
        "line vty 0 4\n"
        " access-class MGMT-ACL in\n"
    )
    findings = acl_checks.check_acl_applied_to_management(text)
    assert len(findings) == 1
    assert findings[0].rule == "acl_blocks_management_access"


# --------------------------------------------------------------------------
# NAT
# --------------------------------------------------------------------------
def test_nat_inside_outside_missing_detected():
    text = (
        "interface GigabitEthernet0/0\n"
        " ip address 192.168.1.1 255.255.255.0\n"
        "interface GigabitEthernet0/1\n"
        " ip address 203.0.113.10 255.255.255.252\n"
        "ip nat inside source list 1 interface GigabitEthernet0/1 overload\n"
    )
    findings = nat_checks.check_nat_inside_outside(text)
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"


def test_nat_inside_outside_present_not_flagged():
    text = (
        "interface GigabitEthernet0/0\n"
        " ip nat inside\n"
        "interface GigabitEthernet0/1\n"
        " ip nat outside\n"
        "ip nat inside source list 1 interface GigabitEthernet0/1 overload\n"
    )
    assert nat_checks.check_nat_inside_outside(text) == []


def test_nat_overload_missing_on_dynamic_rule():
    text = "ip nat inside source list 1 pool PUBLIC-POOL\n"
    findings = nat_checks.check_nat_overload(text)
    assert len(findings) == 1
    assert findings[0].rule == "nat_overload_missing"


def test_nat_overload_present_not_flagged():
    text = "ip nat inside source list 1 pool PUBLIC-POOL overload\n"
    assert nat_checks.check_nat_overload(text) == []


def test_nat_static_only_flagged_as_overload_missing():
    text = "ip nat inside source static 192.168.1.10 203.0.113.10\n"
    findings = nat_checks.check_nat_overload(text)
    assert len(findings) == 1


# --------------------------------------------------------------------------
# DHCP
# --------------------------------------------------------------------------
def test_dhcp_pool_missing_detected():
    text = "% No DHCP pools configured\n"
    findings = dhcp_checks.check_dhcp_pool_missing(text)
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"


def test_dhcp_excluded_range_near_exhaustion():
    text = (
        "network 10.10.10.0 255.255.255.0\n"
        "ip dhcp excluded-address 10.10.10.1 10.10.10.250\n"
    )
    findings = dhcp_checks.check_dhcp_excluded_range(text)
    assert len(findings) == 1
    assert findings[0].rule == "dhcp_excluded_range"


def test_dhcp_excluded_small_range_not_flagged():
    text = (
        "network 10.10.10.0 255.255.255.0\n"
        "ip dhcp excluded-address 10.10.10.1 10.10.10.10\n"
    )
    assert dhcp_checks.check_dhcp_excluded_range(text) == []


# --------------------------------------------------------------------------
# Port security
# --------------------------------------------------------------------------
def test_port_security_violation_detected():
    text = (
        "Port Security              : Enabled\n"
        "Port Status                : Secure-shutdown\n"
        "Maximum MAC Addresses       : 1\n"
        "Security Violation Count    : 1\n"
    )
    findings = security_checks.check_port_security_violation(text)
    assert len(findings) == 1


def test_port_security_normal_not_flagged():
    text = "Port Status                : Secure-up\n"
    assert security_checks.check_port_security_violation(text) == []


# --------------------------------------------------------------------------
# Determinism & dataset-wide sanity
# --------------------------------------------------------------------------
def test_checker_is_deterministic_same_input_same_output():
    case = load_case("VLAN-001")
    result_1 = [f.to_dict() for f in run_checks(case)]
    result_2 = [f.to_dict() for f in run_checks(case)]
    assert result_1 == result_2


def test_checker_never_crashes_on_any_dataset_case():
    for case in load_cases():
        findings = run_checks(case)
        assert isinstance(findings, list)


def test_dataset_has_at_least_30_cases():
    assert len(load_cases()) >= 30


def test_build_evidence_text_excludes_ground_truth_fields():
    case = load_case("VLAN-001")
    text = build_evidence_text(case)
    # The evidence text handed to checks/AI must never include the
    # answer key fields - only symptom/topology/show_outputs.
    assert case["expected_fault"] not in text
