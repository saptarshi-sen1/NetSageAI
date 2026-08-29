"""
Tests for the case dataset (data/cases.csv) - structural integrity, not
networking correctness (that's inherently a matter of domain judgment,
which is exactly why human review exists).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.case_service import list_cases

REQUIRED_FIELDS = [
    "case_id", "title", "symptom", "topology_note", "show_outputs",
    "expected_fault", "osi_layer", "concept", "severity",
    "expected_evidence", "expected_next_command", "expected_fix",
    "verification_command", "difficulty",
]

VALID_SEVERITIES = {"Low", "Medium", "High", "Critical"}
VALID_DIFFICULTIES = {"Easy", "Medium", "Hard"}
VALID_OSI_LAYERS = {"Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 7"}


def test_at_least_thirty_cases():
    cases = list_cases()
    assert len(cases) >= 30


def test_case_ids_are_unique():
    cases = list_cases()
    ids = [c["case_id"] for c in cases]
    assert len(ids) == len(set(ids))


def test_every_case_has_all_required_fields_nonempty():
    cases = list_cases()
    for case in cases:
        for field in REQUIRED_FIELDS:
            assert field in case, f"{case.get('case_id')} missing field {field}"
            assert case[field].strip() != "", f"{case.get('case_id')} has empty {field}"


def test_severity_values_are_valid():
    for case in list_cases():
        assert case["severity"] in VALID_SEVERITIES, case["case_id"]


def test_difficulty_values_are_valid():
    for case in list_cases():
        assert case["difficulty"] in VALID_DIFFICULTIES, case["case_id"]


def test_osi_layer_values_are_recognizable():
    for case in list_cases():
        # Some cases legitimately span/describe an ambiguous layer in
        # prose (e.g. "Layer 2/3 (undetermined)" style notes only ever
        # appear in AI output, never in the dataset itself) - the
        # dataset itself should always use a clean single-layer label.
        assert any(layer in case["osi_layer"] for layer in VALID_OSI_LAYERS), case["case_id"]


def test_dataset_covers_required_concept_categories():
    cases = list_cases()
    concepts = {c["concept"] for c in cases}
    required_concepts = {
        "VLAN", "Default Gateway", "DHCP", "DNS", "Static Routing",
        "Dynamic Routing", "ACL", "NAT", "Trunking", "Interface State",
        "Subnetting", "IP Addressing", "Inter-VLAN Routing", "Wireless",
        "Routing", "STP", "Port Security",
    }
    missing = required_concepts - concepts
    assert not missing, f"Dataset is missing coverage for: {missing}"


def test_show_outputs_look_like_real_cisco_output():
    """Loose sanity check: every case's show_outputs should contain at
    least one recognizable `show` command invocation."""
    show_command_markers = (
        "show ip", "show vlan", "show interfaces", "show run",
        "show access-lists", "show mac", "show port-security", "show wlan",
        "show spanning-tree", "ipconfig",
    )
    for case in list_cases():
        text = case["show_outputs"]
        assert any(marker in text for marker in show_command_markers), (
            f"{case['case_id']} show_outputs doesn't look like real Cisco output"
        )
