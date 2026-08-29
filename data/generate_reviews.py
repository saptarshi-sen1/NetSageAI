"""
Seeds data/reviews.csv with realistic prior review history so the
dashboard and Responsible AI log have data to show immediately,
without requiring a live API key.

Run: python3 generate_reviews.py
"""
import csv
import os

FIELDS = [
    "review_id", "case_id", "ai_root_cause", "ai_confidence",
    "human_decision", "human_root_cause", "correction_reason",
    "reviewer", "timestamp", "verification_status", "evidence_missed",
]

ROWS = [
    # --- ACCEPTED cases: AI diagnosis matched evidence, human agreed -------
    dict(
        review_id="REV-0001", case_id="VLAN-001",
        ai_root_cause=(
            "Fa0/6 is a static access port assigned to VLAN 20 instead "
            "of VLAN 10, placing PC-A in a different broadcast domain "
            "than FileServer1."
        ),
        ai_confidence=0.88,
        human_decision="ACCEPTED",
        human_root_cause="",
        correction_reason="",
        reviewer="J. Alvarez (Instructor)",
        timestamp="2026-07-14T09:12:00Z",
    ),
    dict(
        review_id="REV-0002", case_id="IFACE-001",
        ai_root_cause=(
            "GigabitEthernet0/0 on RemoteR is administratively down, "
            "isolating the entire office subnet."
        ),
        ai_confidence=0.95,
        human_decision="ACCEPTED",
        human_root_cause="",
        correction_reason="",
        reviewer="J. Alvarez (Instructor)",
        timestamp="2026-07-14T09:20:00Z",
    ),
    dict(
        review_id="REV-0003", case_id="ROUTE-002",
        ai_root_cause=(
            "EdgeR has no default route; Gateway of last resort is not "
            "set despite a healthy link to the ISP."
        ),
        ai_confidence=0.9,
        human_decision="ACCEPTED",
        human_root_cause="",
        correction_reason="",
        reviewer="M. Chen (TA)",
        timestamp="2026-07-15T14:02:00Z",
    ),
    dict(
        review_id="REV-0004", case_id="TRUNK-001",
        ai_root_cause=(
            "SW2's Gi0/1 is a static access port in VLAN 1 rather than "
            "a trunk, so VLAN 10 traffic from SW1 cannot cross to SW2."
        ),
        ai_confidence=0.85,
        human_decision="ACCEPTED",
        human_root_cause="",
        correction_reason="",
        reviewer="M. Chen (TA)",
        timestamp="2026-07-15T14:11:00Z",
    ),
    dict(
        review_id="REV-0005", case_id="SEC-001",
        ai_root_cause=(
            "Fa0/15 entered Secure-shutdown after a port-security "
            "violation when a second MAC address appeared on a "
            "single-MAC-limited port."
        ),
        ai_confidence=0.93,
        human_decision="ACCEPTED",
        human_root_cause="",
        correction_reason="",
        reviewer="J. Alvarez (Instructor)",
        timestamp="2026-07-16T10:45:00Z",
    ),

    # --- EDITED cases: AI was directionally right but needed refinement ---
    dict(
        review_id="REV-0006", case_id="NAT-002",
        ai_root_cause=(
            "The NAT pool is too small for the number of inside hosts, "
            "causing intermittent internet loss."
        ),
        ai_confidence=0.62,
        human_decision="EDITED",
        human_root_cause=(
            "The NAT pool statement is missing the 'overload' keyword. "
            "It's not just pool size - without overload, each public "
            "address can only serve ONE inside host at a time instead "
            "of being shared via PAT, so exhaustion happens far faster "
            "than the raw pool-size math would suggest."
        ),
        correction_reason=(
            "AI correctly spotted pool exhaustion from the miss counter "
            "but didn't call out the missing overload keyword as the "
            "specific configuration defect. Edited to name the exact "
            "line to fix rather than a general capacity explanation."
        ),
        reviewer="M. Chen (TA)",
        timestamp="2026-07-16T15:30:00Z",
    ),
    dict(
        review_id="REV-0007", case_id="MASK-001",
        ai_root_cause=(
            "PC-D has an incorrect subnet mask that prevents it from "
            "communicating with other hosts on the VLAN."
        ),
        ai_confidence=0.7,
        human_decision="EDITED",
        human_root_cause=(
            "PC-D's mask is 255.255.255.192 (/26) versus the rest of "
            "the VLAN's 255.255.255.0 (/24). Edited to specify the "
            "exact mismatched values so the student fixes the right "
            "field instead of guessing which mask is 'correct'."
        ),
        correction_reason=(
            "AI identified the right category of fault but stated it "
            "too generally to act on directly. Reviewer added the "
            "specific observed values from the evidence."
        ),
        reviewer="J. Alvarez (Instructor)",
        timestamp="2026-07-17T11:05:00Z",
    ),
    dict(
        review_id="REV-0008", case_id="WIFI-002",
        ai_root_cause=(
            "Guest devices cannot reach the printer because of a "
            "wireless configuration problem on the WLAN."
        ),
        ai_confidence=0.55,
        human_decision="EDITED",
        human_root_cause=(
            "This is not a misconfiguration - P2P Blocking Action is "
            "intentionally set to Drop on the GuestWiFi profile for "
            "security. Edited to reclassify this as a policy/design "
            "trade-off requiring a stakeholder decision, not a defect "
            "to silently fix."
        ),
        correction_reason=(
            "AI treated an intentional security control as a bug. "
            "Edited so the case is framed correctly: confirm whether "
            "guest printing should be allowed before changing anything."
        ),
        reviewer="M. Chen (TA)",
        timestamp="2026-07-17T16:40:00Z",
    ),

    # --- REJECTED cases: AI diagnosis was wrong, human overrode it --------
    dict(
        review_id="REV-0009", case_id="ACL-002",
        ai_root_cause=(
            "The intranet portal was unreachable because of a routing "
            "problem between the users' subnet and the server subnet."
        ),
        ai_confidence=0.58,
        human_decision="REJECTED",
        human_root_cause=(
            "Routing was never the issue. show access-lists WEB-FILTER "
            "showed an explicit 'deny tcp any any eq 80' applied "
            "inbound on the users' interface. The true fault is the "
            "ACL blocking HTTP, which also explains why SMB file "
            "sharing to the same server kept working."
        ),
        correction_reason=(
            "AI overweighted the 'can't reach one service on a server' "
            "symptom toward a routing explanation and did not "
            "sufficiently use the supplied show access-lists output, "
            "which directly contained the answer."
        ),
        reviewer="J. Alvarez (Instructor)",
        timestamp="2026-07-18T09:55:00Z",
    ),
    dict(
        review_id="REV-0010", case_id="DNS-001",
        ai_root_cause=(
            "DNS was unreachable because of a routing problem between "
            "PC-C and the DNS server."
        ),
        ai_confidence=0.5,
        human_decision="REJECTED",
        human_root_cause=(
            "Routing was fine - PC-C successfully pinged 8.8.8.8 by "
            "IP, which rules out a routing fault. show run confirmed "
            "the DHCP pool was hard-coded to advertise dns-server "
            "10.10.10.99, a non-existent host, instead of the real "
            "internal DNS server at 10.10.10.53."
        ),
        correction_reason=(
            "AI overweighted the 'name resolution fails' symptom and "
            "failed to use the successful raw-IP ping as evidence "
            "against a routing cause, and did not cross-check the "
            "DHCP pool's dns-server value against the known-correct "
            "DNS host."
        ),
        reviewer="M. Chen (TA)",
        timestamp="2026-07-18T13:20:00Z",
    ),
    dict(
        review_id="REV-0011", case_id="STP-001",
        ai_root_cause=(
            "The backup uplink Gi0/2 is misconfigured and stuck in a "
            "blocking state, which should be fixed by disabling "
            "spanning-tree on that port."
        ),
        ai_confidence=0.4,
        human_decision="REJECTED",
        human_root_cause=(
            "Gi0/2 in the Alternate/Blocking role is correct, expected "
            "STP behavior, not a misconfiguration - disabling STP on "
            "that port would risk a Layer 2 loop. The real explanation "
            "for the outage window is normal STP re-convergence delay "
            "while SW-Core reboots."
        ),
        correction_reason=(
            "AI misinterpreted a healthy, working-as-designed STP role "
            "as a fault and recommended a change that would have "
            "introduced a bridging loop risk. This is a case where the "
            "AI's suggested 'fix' would have made the network less "
            "safe, underscoring why human review is mandatory before "
            "any change is applied."
        ),
        reviewer="J. Alvarez (Instructor)",
        timestamp="2026-07-19T10:10:00Z",
    ),
    dict(
        review_id="REV-0012", case_id="DUPIP-001",
        ai_root_cause=(
            "PC-F is losing connectivity due to a failing network "
            "cable or NIC, consistent with the intermittent symptom."
        ),
        ai_confidence=0.35,
        human_decision="REJECTED",
        human_root_cause=(
            "show ip arp showed two different MAC addresses both "
            "mapped to 10.10.10.20 - a textbook duplicate IP conflict "
            "with Printer1, not a hardware fault."
        ),
        correction_reason=(
            "AI defaulted to a generic 'intermittent = hardware' "
            "explanation and did not inspect the supplied ARP table "
            "output, which directly contained the duplicate-IP "
            "evidence needed for a correct diagnosis."
        ),
        reviewer="M. Chen (TA)",
        timestamp="2026-07-20T08:47:00Z",
    ),
]

# Post-processing: assign verification_status and evidence_missed
# without rewriting every dict literal above. Defaults to
# NOT_VERIFIED/"" for every row; overridden below for specific rows to
# demonstrate the full case lifecycle (including a couple of cases that
# were reviewed AND subsequently verified) and to give the "Evidence
# Missed" field real content on the corrected (EDITED/REJECTED) cases -
# see docs/responsible_ai.md for why these specific corrections matter.
VERIFICATION_OVERRIDES = {
    # A few accepted diagnoses that were actually verified after the fix.
    "REV-0001": "VERIFIED",
    "REV-0002": "VERIFIED",
    "REV-0005": "VERIFIED",
    # One accepted diagnosis where the suggested fix was tried and the
    # symptom persisted - demonstrates that "Accepted" and "Verified"
    # are genuinely different signals, not the same thing restated.
    "REV-0004": "VERIFICATION_FAILED",
}

EVIDENCE_MISSED = {
    "REV-0009": (
        "The 'deny tcp any any eq 80' line in show access-lists WEB-FILTER "
        "was present in the evidence the AI was given but wasn't cited in "
        "its reasoning at all."
    ),
    "REV-0010": (
        "The successful 'ping 8.8.8.8' by raw IP (which rules out a routing "
        "fault) and the DHCP pool's dns-server value were both in the "
        "supplied evidence but not used to challenge the routing hypothesis."
    ),
    "REV-0011": (
        "show spanning-tree vlan 10 showing Gi0/2 in the Alternate/Blocking "
        "role was present but its significance as NORMAL STP behavior was "
        "misread as a fault."
    ),
    "REV-0012": (
        "show ip arp, showing two distinct MAC addresses mapped to the same "
        "IP, was supplied but never inspected before defaulting to a "
        "generic hardware explanation."
    ),
    "REV-0006": (
        "The absence of the 'overload' keyword on the ip nat inside source "
        "line was visible in the running-config excerpt but not called out "
        "specifically."
    ),
    "REV-0007": (
        "The peer PC's differing subnet mask value in the second ipconfig "
        "block was present but not directly quoted in the diagnosis."
    ),
    "REV-0008": (
        "The 'P2P Blocking Action: Drop' field in show wlan 3 was supplied "
        "but its status as an intentional security control (not a bug) "
        "wasn't recognized."
    ),
}

for _row in ROWS:
    _row.setdefault(
        "verification_status", VERIFICATION_OVERRIDES.get(_row["review_id"], "NOT_VERIFIED")
    )
    _row.setdefault("evidence_missed", EVIDENCE_MISSED.get(_row["review_id"], ""))


def main():
    out_path = os.path.join(os.path.dirname(__file__), "reviews.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in ROWS:
            writer.writerow(row)
    print(f"Wrote {len(ROWS)} seed reviews to {out_path}")


if __name__ == "__main__":
    main()
