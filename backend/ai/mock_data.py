"""
Scripted mock diagnoses for cases that already have review history in
data/reviews.csv. These intentionally reproduce the same (wrong or
under-specified) AI output a human reviewer already corrected, so that
running the demo in mock mode tells a consistent story: the AI makes
the same mistake, and the review log shows how a human caught it.

Every other case gets a mock diagnosis generated programmatically from
its ground-truth `expected_*` fields - see generate_mock_diagnosis() in
client.py. Both paths are pure functions of the case data, so mock mode
is fully deterministic: same case_id always produces the same output.
"""

# Cases where the human REJECTED the AI's diagnosis outright.
SCRIPTED_REJECTED = {
    "ACL-002": {
        "root_cause": (
            "The intranet portal was unreachable because of a routing "
            "problem between the users' subnet and the server subnet."
        ),
        "confidence": 0.58,
        "confidence_label": "Medium",
        "osi_layer": "Layer 3",
        "concept": "Routing",
        "evidence": [
            "Users report the intranet portal is unreachable from their subnet",
        ],
        "reasoning_summary": (
            "Since the portal is unreachable across subnets, a routing "
            "issue between the user and server networks is a plausible "
            "explanation."
        ),
        "next_command": "show ip route",
        "fix_steps": ["Review the routing table between the two subnets"],
        "verification_steps": ["Ping across subnets after any routing change"],
        "human_review_required": True,
    },
    "DNS-001": {
        "root_cause": (
            "DNS was unreachable because of a routing problem between "
            "PC-C and the DNS server."
        ),
        "confidence": 0.5,
        "confidence_label": "Medium",
        "osi_layer": "Layer 3",
        "concept": "Routing",
        "evidence": [
            "PC-C cannot resolve hostnames",
        ],
        "reasoning_summary": (
            "Name resolution failures can result from an inability to "
            "reach the DNS server at the network layer."
        ),
        "next_command": "show ip route",
        "fix_steps": ["Verify routing between PC-C's subnet and the DNS server"],
        "verification_steps": ["nslookup a hostname from PC-C after any change"],
        "human_review_required": True,
    },
    "STP-001": {
        "root_cause": (
            "The backup uplink Gi0/2 is misconfigured and stuck in a "
            "blocking state; disabling spanning-tree on that port should "
            "resolve the outage."
        ),
        "confidence": 0.4,
        "confidence_label": "Low",
        "osi_layer": "Layer 2",
        "concept": "STP",
        "evidence": [
            "show spanning-tree vlan 10 shows Gi0/2 in BLK status",
        ],
        "reasoning_summary": (
            "A blocked port is not forwarding traffic, which is "
            "consistent with the reported outage during failover."
        ),
        "next_command": "",
        "fix_steps": ["Disable spanning-tree on Gi0/2 so it forwards immediately"],
        "verification_steps": ["Confirm Gi0/2 is forwarding after the change"],
        "human_review_required": True,
    },
    "DUPIP-001": {
        "root_cause": (
            "PC-F is losing connectivity due to a failing network cable "
            "or NIC, consistent with the intermittent symptom."
        ),
        "confidence": 0.35,
        "confidence_label": "Low",
        "osi_layer": "Layer 1",
        "concept": "Physical",
        "evidence": [
            "PC-F reports intermittent connectivity loss",
        ],
        "reasoning_summary": (
            "Intermittent connectivity issues are often caused by a "
            "marginal physical connection."
        ),
        "next_command": "show interfaces (check for CRC/input errors)",
        "fix_steps": ["Replace the patch cable and retest"],
        "verification_steps": ["Monitor for continued drops after cable replacement"],
        "human_review_required": True,
    },
}

# Cases where the human EDITED the AI's diagnosis (right idea, needed refinement).
SCRIPTED_EDITED = {
    "NAT-002": {
        "root_cause": (
            "The NAT pool is too small for the number of inside hosts, "
            "causing intermittent internet loss."
        ),
        "confidence": 0.62,
        "confidence_label": "Medium",
        "osi_layer": "Layer 3",
        "concept": "NAT",
        "evidence": [
            "show ip nat statistics shows the 4-address pool at 100% allocation with a nonzero miss counter",
        ],
        "reasoning_summary": (
            "A fully-allocated NAT pool with misses suggests the pool "
            "does not have enough addresses for the number of hosts "
            "using it."
        ),
        "next_command": "show run | section ip nat",
        "fix_steps": ["Add more public addresses to the NAT pool"],
        "verification_steps": ["Monitor show ip nat statistics under full load"],
        "human_review_required": True,
    },
    "MASK-001": {
        "root_cause": (
            "PC-D has an incorrect subnet mask that prevents it from "
            "communicating with other hosts on the VLAN."
        ),
        "confidence": 0.7,
        "confidence_label": "Medium",
        "osi_layer": "Layer 3",
        "concept": "Subnetting",
        "evidence": [
            "PC-D's ipconfig shows a subnet mask that differs from a peer PC's",
        ],
        "reasoning_summary": (
            "A subnet mask mismatch changes how a host calculates which "
            "addresses are local versus remote, which can block peer "
            "communication."
        ),
        "next_command": "ipconfig on additional peer PCs",
        "fix_steps": ["Correct PC-D's subnet mask to match the rest of the VLAN"],
        "verification_steps": ["Ping between PC-D and peers after the fix"],
        "human_review_required": True,
    },
    "WIFI-002": {
        "root_cause": (
            "Guest devices cannot reach the printer because of a "
            "wireless configuration problem on the WLAN."
        ),
        "confidence": 0.55,
        "confidence_label": "Medium",
        "osi_layer": "Layer 2",
        "concept": "Wireless",
        "evidence": [
            "Guest clients can browse the internet but cannot reach the printer",
        ],
        "reasoning_summary": (
            "Since guests can reach the internet but not a device on "
            "their own VLAN, some wireless-side configuration is likely "
            "preventing that specific path."
        ),
        "next_command": "show wlan (guest profile)",
        "fix_steps": ["Review the guest WLAN configuration for the printer's segment"],
        "verification_steps": ["Attempt print discovery from a guest client"],
        "human_review_required": True,
    },
}
