"""
Generates data/cases.csv for NetSage AI.
Run: python3 generate_cases.py
Produces a deterministic, hand-authored dataset of 30 realistic
Cisco Packet Tracer style troubleshooting cases.
"""
import csv
import os

FIELDS = [
    "case_id", "title", "symptom", "topology_note", "show_outputs",
    "expected_fault", "osi_layer", "concept", "severity",
    "expected_evidence", "expected_next_command", "expected_fix",
    "verification_command", "difficulty",
    "status", "source", "created_at", "updated_at", "created_by",
]

SEED_TIMESTAMP = "2026-06-01T00:00:00Z"

CASES = []


def add(**kwargs):
    row = {k: kwargs.get(k, "") for k in FIELDS}
    row["status"] = "active"
    row["source"] = "seed"
    row["created_at"] = SEED_TIMESTAMP
    row["updated_at"] = SEED_TIMESTAMP
    row["created_by"] = "NetSage AI Course Dataset"
    CASES.append(row)


# ---------------------------------------------------------------------------
# 1. VLAN - access port assigned to the wrong VLAN
# ---------------------------------------------------------------------------
add(
    case_id="VLAN-001",
    title="PC on wrong VLAN cannot reach file server",
    symptom=(
        "PC-A gets an IP address from DHCP and can ping its own default "
        "gateway, but cannot reach FileServer1 (10.10.10.50), which other "
        "PCs in the same office reach without issue."
    ),
    topology_note=(
        "PC-A is connected to SW1 Fa0/6. SW1 Fa0/6 should be in VLAN 10 "
        "(Sales) with FileServer1. SW1 uplinks to R1 on Gi0/1 as an 802.1Q "
        "trunk carrying VLANs 10,20,30."
    ),
    show_outputs=(
        "SW1# show vlan brief\n"
        "VLAN Name                             Status    Ports\n"
        "---- -------------------------------- --------- -------------------------------\n"
        "1    default                          active    Fa0/1, Fa0/2\n"
        "10   Sales                            active    Fa0/3, Fa0/4, Fa0/5\n"
        "20   Engineering                      active    Fa0/6, Fa0/7\n"
        "30   Guest                            active    Fa0/8\n\n"
        "SW1# show interfaces fa0/6 switchport\n"
        "Name: Fa0/6\n"
        "Switchport: Enabled\n"
        "Administrative Mode: static access\n"
        "Operational Mode: static access\n"
        "Access Mode VLAN: 20 (Engineering)\n"
        "Voice VLAN: none\n"
    ),
    expected_fault=(
        "Fa0/6 (PC-A's port) is statically assigned to VLAN 20 "
        "(Engineering) instead of VLAN 10 (Sales), placing PC-A in a "
        "different broadcast domain than FileServer1."
    ),
    osi_layer="Layer 2",
    concept="VLAN",
    severity="Medium",
    expected_evidence=(
        "show vlan brief confirms VLAN 10 exists and holds FileServer1's "
        "segment; show interfaces fa0/6 switchport shows Fa0/6 access VLAN "
        "is 20, not 10."
    ),
    expected_next_command="show mac address-table interface fa0/6",
    expected_fix="switchport access vlan 10 on interface Fa0/6",
    verification_command="show vlan brief; then ping 10.10.10.50 from PC-A",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 2. Default gateway - host has no/blank gateway configured
# ---------------------------------------------------------------------------
add(
    case_id="GW-001",
    title="PC cannot leave local subnet, gateway field blank",
    symptom=(
        "PC-B (10.10.20.15/24) can ping other PCs on the same VLAN 20 "
        "segment but cannot ping anything outside the subnet, including "
        "the router interface."
    ),
    topology_note=(
        "PC-B connects to SW2 Fa0/3 (VLAN 20). R1 subinterface Gi0/1.20 "
        "is 10.10.20.1/24, the intended default gateway for VLAN 20."
    ),
    show_outputs=(
        "PC-B> ipconfig /all\n"
        "IP Address..........: 10.10.20.15\n"
        "Subnet Mask..........: 255.255.255.0\n"
        "Default Gateway......: \n"
        "DNS Servers..........: 10.10.20.1\n\n"
        "R1# show ip interface brief\n"
        "Interface              IP-Address      OK? Method Status    Protocol\n"
        "GigabitEthernet0/1.20  10.10.20.1      YES manual up        up\n"
    ),
    expected_fault=(
        "PC-B has no default gateway configured (blank field), so any "
        "traffic destined outside 10.10.20.0/24 cannot be routed off the "
        "local segment."
    ),
    osi_layer="Layer 3",
    concept="Default Gateway",
    severity="High",
    expected_evidence=(
        "ipconfig /all on PC-B shows an empty Default Gateway field even "
        "though R1's subinterface 10.10.20.1 is up/up and reachable on "
        "the same subnet."
    ),
    expected_next_command="ping 10.10.20.1 from PC-B",
    expected_fix="Set PC-B's default gateway to 10.10.20.1",
    verification_command="ipconfig on PC-B; ping 10.10.20.1; tracert to an external host",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 3. DHCP - DHCP service not running / no pool configured
# ---------------------------------------------------------------------------
add(
    case_id="DHCP-001",
    title="New PCs get APIPA addresses instead of DHCP leases",
    symptom=(
        "All newly connected PCs in VLAN 30 receive 169.254.x.x addresses "
        "instead of addresses in the expected 10.10.30.0/24 range."
    ),
    topology_note=(
        "R1 is configured to act as the DHCP server for VLAN 30 clients "
        "connected through SW3."
    ),
    show_outputs=(
        "R1# show ip dhcp pool\n"
        "% No DHCP pools configured\n\n"
        "R1# show running-config | include ip dhcp\n"
        "R1# show ip interface brief\n"
        "Interface              IP-Address      OK? Method Status    Protocol\n"
        "GigabitEthernet0/1.30  10.10.30.1      YES manual up        up\n"
    ),
    expected_fault=(
        "No DHCP pool exists on R1 for the 10.10.30.0/24 network, so "
        "clients time out on DHCPDISCOVER and self-assign an APIPA "
        "address."
    ),
    osi_layer="Layer 7",
    concept="DHCP",
    severity="Critical",
    expected_evidence=(
        "show ip dhcp pool returns no configured pools, while the "
        "gateway interface Gi0/1.30 is up with the correct network."
    ),
    expected_next_command="show running-config | section dhcp",
    expected_fix=(
        "Create pool: ip dhcp pool VLAN30; network 10.10.30.0 255.255.255.0; "
        "default-router 10.10.30.1; dns-server 8.8.8.8"
    ),
    verification_command="show ip dhcp binding; ipconfig /renew on client",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 4. DNS - wrong DNS server IP handed out / configured
# ---------------------------------------------------------------------------
add(
    case_id="DNS-001",
    title="PCs can ping by IP but 'website not found' by name",
    symptom=(
        "PC-C can successfully ping 8.8.8.8 and other external IPs, but "
        "browsing to www.internal-app.local or any hostname fails with "
        "a name resolution error."
    ),
    topology_note=(
        "PC-C is a DHCP client on VLAN 10. R1 is the DHCP server. The "
        "intended internal DNS server is Server1 at 10.10.10.53."
    ),
    show_outputs=(
        "PC-C> ipconfig /all\n"
        "IP Address..........: 10.10.10.25\n"
        "Default Gateway......: 10.10.10.1\n"
        "DNS Servers..........: 10.10.10.99\n\n"
        "PC-C> ping 8.8.8.8\n"
        "Reply from 8.8.8.8: bytes=32 time=1ms TTL=118\n\n"
        "R1# show run | section dhcp pool VLAN10\n"
        "ip dhcp pool VLAN10\n"
        " network 10.10.10.0 255.255.255.0\n"
        " default-router 10.10.10.1\n"
        " dns-server 10.10.10.99\n"
    ),
    expected_fault=(
        "The DHCP pool hands out DNS server 10.10.10.99, which is not "
        "Server1 (10.10.10.53) and does not respond to DNS queries, so "
        "name resolution fails while raw IP connectivity is fine."
    ),
    osi_layer="Layer 7",
    concept="DNS",
    severity="Medium",
    expected_evidence=(
        "ipconfig /all shows DNS Servers 10.10.10.99; raw ping to 8.8.8.8 "
        "succeeds (ruling out routing); dhcp pool config confirms "
        "dns-server 10.10.10.99 is being advertised instead of .53."
    ),
    expected_next_command="ping 10.10.10.99 and ping 10.10.10.53 from R1",
    expected_fix="Change dns-server to 10.10.10.53 in dhcp pool VLAN10, then have clients renew",
    verification_command="nslookup www.internal-app.local on PC-C after renew",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 5. Static routing - missing static route to remote network
# ---------------------------------------------------------------------------
add(
    case_id="ROUTE-001",
    title="Branch router cannot reach HQ server subnet",
    symptom=(
        "PCs at the branch site can reach each other and the branch "
        "router, but cannot reach the HQ server subnet 172.16.5.0/24."
    ),
    topology_note=(
        "BranchR connects to HQR via a serial link (Se0/0/0, "
        "192.168.100.2/30). HQR owns 172.16.5.0/24 on its LAN. No "
        "dynamic routing protocol is in use; routes are static."
    ),
    show_outputs=(
        "BranchR# show ip route\n"
        "Gateway of last resort is not set\n\n"
        "     172.16.1.0/24 is directly connected, GigabitEthernet0/0\n"
        "     192.168.100.0/30 is directly connected, Serial0/0/0\n\n"
        "BranchR# ping 192.168.100.1\n"
        "!!!!!\n"
        "Success rate is 100 percent\n\n"
        "BranchR# ping 172.16.5.10\n"
        ".....\n"
        "Success rate is 0 percent\n"
    ),
    expected_fault=(
        "BranchR has no route to 172.16.5.0/24. The serial link to HQR "
        "is up (192.168.100.1 is reachable), but no static route was "
        "added for the HQ server subnet."
    ),
    osi_layer="Layer 3",
    concept="Static Routing",
    severity="High",
    expected_evidence=(
        "show ip route on BranchR lists only directly connected networks "
        "(172.16.1.0/24 and 192.168.100.0/30); 172.16.5.0/24 is absent. "
        "The next hop 192.168.100.1 is reachable, ruling out a Layer 1/2 fault."
    ),
    expected_next_command="show ip route on HQR to confirm reciprocal route exists",
    expected_fix="ip route 172.16.5.0 255.255.255.0 192.168.100.1 on BranchR",
    verification_command="show ip route; ping 172.16.5.10 from BranchR",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 6. Dynamic routing - OSPF neighbor not forming, network not advertised
# ---------------------------------------------------------------------------
add(
    case_id="OSPF-001",
    title="OSPF routes to remote LAN missing after new router added",
    symptom=(
        "After R3 was added to the network, hosts on R3's LAN "
        "(192.168.30.0/24) cannot be reached from R1's LAN. R1 and R2 "
        "still route to each other fine."
    ),
    topology_note=(
        "R1, R2, and R3 all run OSPF area 0. R2-R3 link is "
        "10.0.23.0/30. R3's LAN is 192.168.30.0/24 on Gi0/0."
    ),
    show_outputs=(
        "R2# show ip ospf neighbor\n"
        "Neighbor ID     Pri   State           Dead Time   Address         Interface\n"
        "1.1.1.1           1   FULL/BDR        00:00:38    10.0.12.1       Gi0/0\n\n"
        "R3# show ip ospf neighbor\n"
        "% No OSPF neighbors found\n\n"
        "R3# show run | section router ospf\n"
        "router ospf 1\n"
        " network 192.168.30.0 0.0.0.255 area 0\n"
    ),
    expected_fault=(
        "R3's OSPF process only advertises its LAN network; the "
        "10.0.23.0/30 transit link to R2 was never added to the OSPF "
        "network statements, so no adjacency forms with R2 and "
        "192.168.30.0/24 is never learned by R1 or R2."
    ),
    osi_layer="Layer 3",
    concept="Dynamic Routing",
    severity="High",
    expected_evidence=(
        "R3 shows no OSPF neighbors at all, and its ospf config only "
        "contains a network statement for 192.168.30.0/24, missing the "
        "10.0.23.0/30 link to R2."
    ),
    expected_next_command="show ip interface brief on R3 to confirm the R2-facing interface is up",
    expected_fix="Add 'network 10.0.23.0 0.0.0.3 area 0' under router ospf 1 on R3",
    verification_command="show ip ospf neighbor on R3; show ip route ospf on R1",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 7. ACL - standard ACL accidentally blocking legitimate management traffic
# ---------------------------------------------------------------------------
add(
    case_id="ACL-001",
    title="Admin workstation locked out of router SSH after ACL change",
    symptom=(
        "The network admin can no longer SSH into R1 from the admin "
        "workstation (10.10.1.50), though the workstation can ping R1's "
        "interface fine."
    ),
    topology_note=(
        "R1's VTY lines reference access-class MGMT-ACL, intended to "
        "permit only the admin subnet 10.10.1.0/24."
    ),
    show_outputs=(
        "R1# show access-lists MGMT-ACL\n"
        "Standard IP access list MGMT-ACL\n"
        "    10 deny   10.10.1.0 0.0.0.255\n"
        "    20 permit any\n\n"
        "R1# show run | section line vty\n"
        "line vty 0 4\n"
        " access-class MGMT-ACL in\n"
        " transport input ssh\n"
    ),
    expected_fault=(
        "MGMT-ACL denies the admin subnet 10.10.1.0/24 (line 10) and "
        "permits everyone else (line 20) - the permit/deny logic is "
        "inverted from what was intended, blocking exactly the admin "
        "workstation that should have access."
    ),
    osi_layer="Layer 4",
    concept="ACL",
    severity="High",
    expected_evidence=(
        "show access-lists MGMT-ACL shows an explicit deny for "
        "10.10.1.0/24 ahead of a permit any, and this ACL is applied "
        "inbound on the VTY lines used for SSH."
    ),
    expected_next_command="show access-lists MGMT-ACL (already sufficient; verify no other ACL on the ingress interface)",
    expected_fix=(
        "Rewrite MGMT-ACL: permit 10.10.1.0 0.0.0.255 then deny any, "
        "or explicitly permit the admin subnet before any deny statement."
    ),
    verification_command="ssh to R1 from 10.10.1.50; show access-lists MGMT-ACL for updated hit counters",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 8. NAT - PAT/overload not configured, only static translation exists
# ---------------------------------------------------------------------------
add(
    case_id="NAT-001",
    title="Only one internal host can reach the internet at a time",
    symptom=(
        "PC1 can browse the internet, but as soon as PC1 is active, PC2 "
        "and PC3 (same inside network) cannot get any external pages to "
        "load, even though they can ping the ISP-facing interface."
    ),
    topology_note=(
        "R1 connects the inside network 192.168.1.0/24 to the ISP via "
        "Gi0/1 (203.0.113.10). PAT/overload was intended for all inside "
        "hosts."
    ),
    show_outputs=(
        "R1# show ip nat translations\n"
        "Pro Inside global      Inside local       Outside local      Outside global\n"
        "--- 203.0.113.10       192.168.1.10       -                  -\n\n"
        "R1# show run | section ip nat\n"
        "ip nat inside source static 192.168.1.10 203.0.113.10\n"
        "interface GigabitEthernet0/0\n"
        " ip nat inside\n"
        "interface GigabitEthernet0/1\n"
        " ip nat outside\n"
    ),
    expected_fault=(
        "Only a single static NAT translation exists (192.168.1.10 to "
        "203.0.113.10). There is no 'ip nat inside source list ... "
        "interface Gi0/1 overload' statement, so no other inside host "
        "can be translated and reach the internet."
    ),
    osi_layer="Layer 3",
    concept="NAT",
    severity="High",
    expected_evidence=(
        "show ip nat translations lists only one static entry for "
        "192.168.1.10; the running-config has a static NAT line but no "
        "overload/PAT pool or access-list based dynamic NAT for the "
        "rest of 192.168.1.0/24."
    ),
    expected_next_command="show access-lists (to see if a NAT-eligible ACL already exists)",
    expected_fix=(
        "Add: access-list 1 permit 192.168.1.0 0.0.0.255; "
        "ip nat inside source list 1 interface GigabitEthernet0/1 overload"
    ),
    verification_command="show ip nat translations while PC2 and PC3 browse simultaneously",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 9. Trunking - trunk link configured as access, VLANs can't cross switches
# ---------------------------------------------------------------------------
add(
    case_id="TRUNK-001",
    title="VLAN 10 users on SW2 cannot reach VLAN 10 users on SW1",
    symptom=(
        "PCs in VLAN 10 on SW1 can talk to each other, and PCs in VLAN "
        "10 on SW2 can talk to each other, but VLAN 10 traffic does not "
        "cross between the two switches."
    ),
    topology_note=(
        "SW1 Gi0/1 and SW2 Gi0/1 are connected directly and are meant "
        "to form an 802.1Q trunk carrying VLANs 10, 20, 30."
    ),
    show_outputs=(
        "SW1# show interfaces trunk\n"
        "Port        Mode             Encapsulation  Status        Native vlan\n"
        "Gi0/1       on               802.1q         trunking      1\n\n"
        "SW2# show interfaces trunk\n"
        "(no output - no trunking interfaces found)\n\n"
        "SW2# show interfaces gi0/1 switchport\n"
        "Name: Gi0/1\n"
        "Switchport: Enabled\n"
        "Administrative Mode: static access\n"
        "Operational Mode: static access\n"
        "Access Mode VLAN: 1 (default)\n"
    ),
    expected_fault=(
        "SW2's Gi0/1 is configured as a static access port in VLAN 1, "
        "not as a trunk. SW1's side is correctly trunking, but a trunk "
        "requires both ends to agree; SW2 is only forwarding VLAN 1 "
        "traffic on that link, so VLAN 10/20/30 frames from SW1 are "
        "dropped at SW2."
    ),
    osi_layer="Layer 2",
    concept="Trunking",
    severity="High",
    expected_evidence=(
        "show interfaces trunk on SW2 returns no trunking ports at all, "
        "and show interfaces gi0/1 switchport confirms Gi0/1 is in "
        "static access mode on VLAN 1, while SW1's Gi0/1 is already "
        "trunking."
    ),
    expected_next_command="show cdp neighbors to confirm SW1-SW2 are directly connected on the expected ports",
    expected_fix=(
        "On SW2 Gi0/1: switchport trunk encapsulation dot1q; "
        "switchport mode trunk"
    ),
    verification_command="show interfaces trunk on both switches; ping across VLAN 10 between switches",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 10. Interface shutdown / administratively down
# ---------------------------------------------------------------------------
add(
    case_id="IFACE-001",
    title="Entire remote office offline after maintenance window",
    symptom=(
        "No device at the remote office can reach anything, including "
        "each other through the router. The office lost connectivity "
        "right after a scheduled maintenance change."
    ),
    topology_note=(
        "RemoteR's LAN-facing interface Gi0/0 serves the office subnet "
        "192.168.50.0/24.",
    ),
    show_outputs=(
        "RemoteR# show ip interface brief\n"
        "Interface              IP-Address      OK? Method Status                  Protocol\n"
        "GigabitEthernet0/0     192.168.50.1    YES manual administratively down   down\n"
        "GigabitEthernet0/1     203.0.113.5     YES manual up                      up\n"
    ),
    expected_fault=(
        "GigabitEthernet0/0, the LAN interface for the office subnet, "
        "is administratively down - almost certainly left shut during "
        "the maintenance window and never re-enabled."
    ),
    osi_layer="Layer 1",
    concept="Interface State",
    severity="Critical",
    expected_evidence=(
        "show ip interface brief shows Gi0/0 status as "
        "'administratively down', while Gi0/1 (the WAN-facing side) is "
        "up/up, isolating the pattern to the LAN interface only."
    ),
    expected_next_command="show running-config interface gi0/0 to confirm no other issues before re-enabling",
    expected_fix="interface GigabitEthernet0/0; no shutdown",
    verification_command="show ip interface brief; ping 192.168.50.1 from an office PC",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 11. Wrong subnet mask - mismatched mask causes host to miscalculate network
# ---------------------------------------------------------------------------
add(
    case_id="MASK-001",
    title="One PC can't reach any teammate, others fine",
    symptom=(
        "PC-D can ping its default gateway but cannot ping any other PC "
        "in the same office, including ones plugged into the same "
        "switch. All other PCs on that switch communicate normally."
    ),
    topology_note=(
        "The office subnet is 192.168.5.0/24 (mask 255.255.255.0). "
        "All PCs including PC-D connect to SW1 in VLAN 5."
    ),
    show_outputs=(
        "PC-D> ipconfig\n"
        "IP Address..........: 192.168.5.40\n"
        "Subnet Mask..........: 255.255.255.192\n"
        "Default Gateway......: 192.168.5.1\n\n"
        "PC-E> ipconfig\n"
        "IP Address..........: 192.168.5.41\n"
        "Subnet Mask..........: 255.255.255.0\n"
        "Default Gateway......: 192.168.5.1\n"
    ),
    expected_fault=(
        "PC-D uses mask 255.255.255.192 (/26) while the rest of the "
        "subnet uses 255.255.255.0 (/24). With a /26 mask, PC-D "
        "computes PC-E (192.168.5.41) as being on a different network "
        "(192.168.5.0/26 vs 192.168.5.64/26 boundary confusion), so it "
        "sends peer traffic to the gateway instead of ARPing directly, "
        "and the gateway has no route back for that mismatched logic."
    ),
    osi_layer="Layer 3",
    concept="Subnetting",
    severity="Medium",
    expected_evidence=(
        "PC-D's subnet mask (255.255.255.192) does not match PC-E's "
        "subnet mask (255.255.255.0) despite both being on the same "
        "physical VLAN and IP range."
    ),
    expected_next_command="ipconfig on two more PCs on the same switch to confirm the mask standard",
    expected_fix="Correct PC-D's subnet mask to 255.255.255.0",
    verification_command="ping between PC-D and PC-E after the mask correction",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 12. Duplicate IP
# ---------------------------------------------------------------------------
add(
    case_id="DUPIP-001",
    title="Intermittent connectivity, Windows shows IP conflict warning",
    symptom=(
        "PC-F intermittently loses network connectivity, and its "
        "taskbar occasionally shows a Windows message about an IP "
        "address conflict with another device on the network."
    ),
    topology_note=(
        "PC-F was statically configured at 10.10.10.20. Printer1 was "
        "also statically configured, by a different technician, "
        "without checking the DHCP exclusion range."
    ),
    show_outputs=(
        "PC-F> ipconfig\n"
        "IP Address..........: 10.10.10.20\n\n"
        "R1# show ip arp | include 10.10.10.20\n"
        "Internet  10.10.10.20        4   00E0.1234.ABCD  ARPA   GigabitEthernet0/0\n"
        "Internet  10.10.10.20        1   00E0.5678.EF01  ARPA   GigabitEthernet0/0\n"
    ),
    expected_fault=(
        "Two different MAC addresses are both mapped to 10.10.10.20 in "
        "the ARP table, confirming a duplicate IP address conflict "
        "between PC-F and Printer1."
    ),
    osi_layer="Layer 3",
    concept="IP Addressing",
    severity="Medium",
    expected_evidence=(
        "show ip arp lists two distinct MAC addresses both claiming "
        "10.10.10.20, which is only possible with a duplicate static "
        "assignment."
    ),
    expected_next_command="show ip dhcp conflict; check Printer1's configured static IP",
    expected_fix="Reassign Printer1 to an unused address outside the DHCP scope, e.g. 10.10.10.240, and add it to ip dhcp excluded-address",
    verification_command="show ip arp; confirm only one MAC maps to 10.10.10.20",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 13. Missing VLAN - VLAN referenced by a port doesn't exist on the switch
# ---------------------------------------------------------------------------
add(
    case_id="VLAN-002",
    title="Newly wired desk has no network access at all",
    symptom=(
        "A newly wired desk plugged into SW4 Fa0/12 gets no link light "
        "response from DHCP and cannot ping anything, including the "
        "switch's own management IP."
    ),
    topology_note=(
        "Fa0/12 was configured for the new Marketing VLAN, VLAN 40, "
        "which was supposed to be created as part of the same change."
    ),
    show_outputs=(
        "SW4# show vlan brief\n"
        "VLAN Name                             Status    Ports\n"
        "---- -------------------------------- --------- -------------------------------\n"
        "1    default                          active    Fa0/1, Fa0/2\n"
        "10   Sales                            active    Fa0/3, Fa0/4\n\n"
        "SW4# show interfaces fa0/12 switchport\n"
        "Name: Fa0/12\n"
        "Administrative Mode: static access\n"
        "Access Mode VLAN: 40 (Inactive)\n"
    ),
    expected_fault=(
        "Fa0/12 is assigned to VLAN 40, but VLAN 40 was never created "
        "with 'vlan 40' in global config - it does not appear in show "
        "vlan brief at all, so the port shows the access VLAN as "
        "'Inactive' and cannot forward traffic."
    ),
    osi_layer="Layer 2",
    concept="VLAN",
    severity="High",
    expected_evidence=(
        "show vlan brief lists only VLAN 1 and VLAN 10 - VLAN 40 is "
        "absent. show interfaces fa0/12 switchport confirms the port's "
        "assigned VLAN 40 is marked (Inactive), the standard symptom "
        "of a port assigned to a non-existent VLAN."
    ),
    expected_next_command="show running-config | section vlan",
    expected_fix="vlan 40; name Marketing (then verify Fa0/12 shows Access Mode VLAN: 40 active)",
    verification_command="show vlan brief; ipconfig /renew on the desk PC",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 14. Native VLAN mismatch on a trunk
# ---------------------------------------------------------------------------
add(
    case_id="TRUNK-002",
    title="Random VLAN 1 traffic bleeding, CDP native VLAN mismatch warning",
    symptom=(
        "Console on SW1 periodically logs a '%CDP-4-NATIVE_VLAN_MISMATCH' "
        "message for Gi0/2, and untagged/VLAN 1 management traffic "
        "occasionally appears where it shouldn't."
    ),
    topology_note=(
        "SW1 Gi0/2 trunks to SW5 Gi0/1, carrying VLANs 1,10,20.",
    ),
    show_outputs=(
        "SW1# show interfaces trunk\n"
        "Port        Mode      Encapsulation  Status       Native vlan\n"
        "Gi0/2       on        802.1q         trunking     1\n\n"
        "SW5# show interfaces trunk\n"
        "Port        Mode      Encapsulation  Status       Native vlan\n"
        "Gi0/1       on        802.1q         trunking     99\n"
    ),
    expected_fault=(
        "SW1's Gi0/2 uses native VLAN 1 while SW5's Gi0/1 uses native "
        "VLAN 99 on the same trunk. A native VLAN mismatch causes "
        "untagged frames to be interpreted as belonging to different "
        "VLANs on each end, leaking traffic between VLAN 1 and VLAN 99."
    ),
    osi_layer="Layer 2",
    concept="Trunking",
    severity="Medium",
    expected_evidence=(
        "show interfaces trunk on SW1 reports native vlan 1 for Gi0/2; "
        "the same trunk's other end on SW5 reports native vlan 99 for "
        "Gi0/1 - the two ends disagree on the native VLAN."
    ),
    expected_next_command="show run interface gi0/2 on both switches to see the native vlan command explicitly",
    expected_fix="switchport trunk native vlan 1 on SW5 Gi0/1 (align both ends to the same native VLAN)",
    verification_command="show interfaces trunk on both switches; confirm CDP native VLAN mismatch log clears",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 15. Access-port VLAN mismatch (server plugged into wrong VLAN port)
# ---------------------------------------------------------------------------
add(
    case_id="VLAN-003",
    title="Server unreachable from its own VLAN's users after a cable move",
    symptom=(
        "Server2 was recently re-patched to a different switch port "
        "during a rack cleanup. Since then, no VLAN 10 client can reach "
        "it, though the server itself reports 'connected' at Layer 1."
    ),
    topology_note=(
        "Server2 (10.10.10.60) should be on a VLAN 10 access port. It "
        "was re-patched into SW2 Fa0/9.",
    ),
    show_outputs=(
        "SW2# show interfaces fa0/9 switchport\n"
        "Name: Fa0/9\n"
        "Administrative Mode: static access\n"
        "Access Mode VLAN: 30 (Guest)\n\n"
        "SW2# show mac address-table interface fa0/9\n"
        "Vlan    Mac Address       Type        Ports\n"
        "30      00d0.bcaa.1111    DYNAMIC     Fa0/9\n"
    ),
    expected_fault=(
        "Fa0/9, the port Server2 was re-patched into, is an access port "
        "in VLAN 30 (Guest), not VLAN 10. Server2's MAC is learned in "
        "VLAN 30, confirming it is physically connected in the wrong "
        "VLAN."
    ),
    osi_layer="Layer 2",
    concept="VLAN",
    severity="High",
    expected_evidence=(
        "show interfaces fa0/9 switchport shows Access Mode VLAN 30; "
        "show mac address-table interface fa0/9 confirms Server2's MAC "
        "was learned on VLAN 30, not VLAN 10."
    ),
    expected_next_command="show vlan brief to find a free VLAN 10 port, or plan to re-tag Fa0/9",
    expected_fix="switchport access vlan 10 on interface Fa0/9 (or re-patch to a known VLAN 10 port)",
    verification_command="show mac address-table interface fa0/9; ping Server2 from a VLAN 10 client",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 16. Inter-VLAN routing - router-on-a-stick subinterface misconfigured
# ---------------------------------------------------------------------------
add(
    case_id="INTERVLAN-001",
    title="VLAN 30 reaches gateway but not VLAN 10 server",
    symptom=(
        "PC in VLAN 30 receives an IP address and can ping its default "
        "gateway, but cannot reach the server in VLAN 10."
    ),
    topology_note=(
        "PC30 is connected to SW1 Fa0/5 (VLAN 30). SW1 connects to R1 "
        "using Gi0/1 as an 802.1Q trunk. Server10 (10.10.10.50) is "
        "connected to SW2 in VLAN 10. R1 uses router-on-a-stick with "
        "subinterfaces for inter-VLAN routing."
    ),
    show_outputs=(
        "R1# show ip interface brief\n"
        "Interface                 IP-Address      OK? Method Status    Protocol\n"
        "GigabitEthernet0/1        unassigned      YES unset  up        up\n"
        "GigabitEthernet0/1.10     unassigned      YES manual up        up\n"
        "GigabitEthernet0/1.30     10.10.30.1      YES manual up        up\n\n"
        "R1# show run interface gi0/1.10\n"
        "interface GigabitEthernet0/1.10\n"
        " encapsulation dot1Q 10\n\n"
        "R1# show interfaces trunk\n"
        "(run on SW1)\n"
        "Port    Mode  Encapsulation  Status     Native vlan\n"
        "Gi0/1   on    802.1q         trunking   1\n"
    ),
    expected_fault=(
        "Subinterface Gi0/1.10 has 'encapsulation dot1Q 10' but no IP "
        "address configured (shown as unassigned), so R1 has no gateway "
        "for VLAN 10 and cannot route between VLAN 30 and VLAN 10, even "
        "though the trunk to SW1 and VLAN 30's subinterface are both fine."
    ),
    osi_layer="Layer 3",
    concept="Inter-VLAN Routing",
    severity="High",
    expected_evidence=(
        "show ip interface brief shows Gi0/1.10 as 'unassigned' for its "
        "IP address while Gi0/1.30 correctly has 10.10.30.1; the trunk "
        "itself is confirmed up, isolating the fault to the missing "
        "VLAN 10 subinterface IP."
    ),
    expected_next_command="show vlan brief on SW2 to confirm Server10 is actually in VLAN 10",
    expected_fix="interface GigabitEthernet0/1.10; ip address 10.10.10.1 255.255.255.0",
    verification_command="show ip interface brief; ping 10.10.10.50 from PC30",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 17. Wireless connectivity - SSID/AP misconfiguration
# ---------------------------------------------------------------------------
add(
    case_id="WIFI-001",
    title="Laptops cannot see the office Wi-Fi network at all",
    symptom=(
        "No laptops in the east wing can see 'CorpWiFi' in their "
        "available network list, though they could last week."
    ),
    topology_note=(
        "AP-East is an autonomous access point wired to SW3 Fa0/4, "
        "broadcasting SSID CorpWiFi on VLAN 10.",
    ),
    show_outputs=(
        "AP-East# show running-config | section dot11 ssid\n"
        "dot11 ssid CorpWiFi\n"
        " vlan 10\n"
        " authentication open\n"
        " guest-mode disable\n\n"
        "AP-East# show interfaces dot11radio 0\n"
        "Dot11Radio0 is administratively down, line protocol is down\n"
    ),
    expected_fault=(
        "The SSID CorpWiFi is configured correctly, but the radio "
        "interface Dot11Radio0 is administratively down, so the AP is "
        "not transmitting at all - no client can see the SSID."
    ),
    osi_layer="Layer 1",
    concept="Wireless",
    severity="Critical",
    expected_evidence=(
        "SSID configuration for CorpWiFi looks correct with "
        "guest-mode disable and vlan 10, but show interfaces dot11radio 0 "
        "reports the radio itself as administratively down."
    ),
    expected_next_command="show interfaces fa0/4 on SW3 to confirm the AP's wired uplink is up",
    expected_fix="interface Dot11Radio0; no shutdown",
    verification_command="show interfaces dot11radio 0; scan for CorpWiFi from a laptop",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 18. Guest Wi-Fi isolation blocking a legitimate use case
# ---------------------------------------------------------------------------
add(
    case_id="WIFI-002",
    title="Guest Wi-Fi users cannot print to the lobby printer",
    symptom=(
        "Guests on the GuestWiFi SSID can browse the internet fine but "
        "cannot discover or print to LobbyPrinter (10.10.99.20), which "
        "is also on the guest VLAN."
    ),
    topology_note=(
        "GuestWiFi maps to VLAN 99. LobbyPrinter is wired into VLAN 99 "
        "on SW6. Client isolation (peer-to-peer blocking) was enabled "
        "on the guest WLAN for security."
    ),
    show_outputs=(
        "WLC# show wlan 3\n"
        "WLAN Identifier.................................. 3\n"
        "Profile Name...................................... GuestWiFi\n"
        "P2P Blocking Action............................... Drop\n"
        "Interface......................................... vlan99\n"
    ),
    expected_fault=(
        "P2P Blocking Action is set to 'Drop' on the GuestWiFi WLAN, "
        "which intentionally blocks client-to-client (and client-to-"
        "device) traffic within the guest VLAN, including to "
        "LobbyPrinter. This is a working-as-designed security feature, "
        "not a fault, but it is the root cause of the symptom."
    ),
    osi_layer="Layer 2",
    concept="Wireless",
    severity="Low",
    expected_evidence=(
        "show wlan 3 confirms P2P Blocking Action is set to Drop on the "
        "GuestWiFi profile bound to vlan99, which is the same VLAN as "
        "LobbyPrinter."
    ),
    expected_next_command="show wlan 3 (already conclusive); confirm with stakeholders whether printing should be allowed",
    expected_fix=(
        "If printing is a desired guest feature: set P2P Blocking "
        "Action to Allow, or move the printer to a small dedicated "
        "'guest services' VLAN excluded from isolation."
    ),
    verification_command="Attempt print discovery from a guest client after the policy change",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 19. Missing default route - edge router has no route to the internet
# ---------------------------------------------------------------------------
add(
    case_id="ROUTE-002",
    title="Entire company can reach internal sites but not the internet",
    symptom=(
        "All internal traffic (site to site) works normally, but no "
        "one anywhere in the company can reach any external website or "
        "public IP address."
    ),
    topology_note=(
        "EdgeR connects the internal network to the ISP router at "
        "203.0.113.1 via Gi0/2.",
    ),
    show_outputs=(
        "EdgeR# show ip route\n"
        "Gateway of last resort is not set\n\n"
        "     10.0.0.0/8 is variably subnetted, 6 subnets, 2 masks\n"
        "        via OSPF, internal networks\n"
        "     203.0.113.0/30 is directly connected, GigabitEthernet0/2\n\n"
        "EdgeR# ping 203.0.113.1\n"
        "!!!!!\n"
        "Success rate is 100 percent\n"
    ),
    expected_fault=(
        "EdgeR has no default route (Gateway of last resort is not "
        "set). Internal OSPF routes exist and the link to the ISP is "
        "up, but there is no 0.0.0.0/0 route pointing to the ISP, so "
        "any destination outside the known internal networks is "
        "unroutable."
    ),
    osi_layer="Layer 3",
    concept="Routing",
    severity="Critical",
    expected_evidence=(
        "show ip route explicitly states 'Gateway of last resort is not "
        "set' and lists no 0.0.0.0/0 entry, while the ISP-facing "
        "interface and next hop (203.0.113.1) are confirmed reachable "
        "by ping."
    ),
    expected_next_command="show run | include ip route (confirm no static default route exists anywhere)",
    expected_fix="ip route 0.0.0.0 0.0.0.0 203.0.113.1",
    verification_command="show ip route; ping 8.8.8.8 from an internal host",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 20. Incorrect gateway handed out by DHCP (different from GW-001)
# ---------------------------------------------------------------------------
add(
    case_id="GW-002",
    title="Whole VLAN 20 lost external access after DHCP pool edit",
    symptom=(
        "Every PC in VLAN 20 can reach each other but none can reach "
        "any other VLAN or the internet. This started right after an "
        "admin edited the DHCP pool to add a new DNS server."
    ),
    topology_note=(
        "R1 Gi0/0.20 is 10.10.20.1/24, the correct gateway for VLAN 20. "
        "R1 is also the DHCP server for VLAN 20.",
    ),
    show_outputs=(
        "R1# show run | section dhcp pool VLAN20\n"
        "ip dhcp pool VLAN20\n"
        " network 10.10.20.0 255.255.255.0\n"
        " default-router 10.10.20.100\n"
        " dns-server 8.8.8.8\n\n"
        "PC-G> ipconfig\n"
        "IP Address..........: 10.10.20.55\n"
        "Default Gateway......: 10.10.20.100\n"
    ),
    expected_fault=(
        "The DHCP pool's default-router was mistakenly set to "
        "10.10.20.100 instead of 10.10.20.1 (R1's real subinterface "
        "IP). No device answers ARP for .100, so nothing beyond the "
        "local VLAN is reachable for any DHCP client."
    ),
    osi_layer="Layer 3",
    concept="Default Gateway",
    severity="High",
    expected_evidence=(
        "The dhcp pool VLAN20 config shows default-router "
        "10.10.20.100; PC-G's ipconfig confirms it received that as its "
        "gateway, but R1's actual subinterface address is 10.10.20.1, "
        "a mismatch."
    ),
    expected_next_command="show ip interface brief on R1 to confirm the real subinterface address",
    expected_fix="Edit dhcp pool VLAN20: default-router 10.10.20.1, then have clients renew",
    verification_command="ipconfig /renew on PC-G; ping 10.10.20.1; ping 8.8.8.8",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 21. DHCP excluded address / pool exhaustion issue
# ---------------------------------------------------------------------------
add(
    case_id="DHCP-002",
    title="Only the first few PCs each morning get an IP address",
    symptom=(
        "Every morning, the first handful of PCs to boot get IP "
        "addresses normally, but PCs booted afterward get APIPA "
        "addresses until the office is rebooted overnight again."
    ),
    topology_note=(
        "VLAN 10 has roughly 40 PCs. The DHCP pool for VLAN 10 covers "
        "10.10.10.0/24.",
    ),
    show_outputs=(
        "R1# show ip dhcp pool VLAN10\n"
        "Pool VLAN10 :\n"
        " Network: 10.10.10.0/24\n"
        " Leased addresses: 6\n\n"
        "R1# show run | section ip dhcp excluded-address\n"
        "ip dhcp excluded-address 10.10.10.1 10.10.10.250\n"
    ),
    expected_fault=(
        "The excluded-address range 10.10.10.1-10.10.10.250 removes "
        "nearly the entire /24 from the usable DHCP pool, leaving only "
        "addresses .251-.254 (a handful) available - explaining why "
        "only a few PCs can lease an address before the pool is "
        "exhausted."
    ),
    osi_layer="Layer 7",
    concept="DHCP",
    severity="High",
    expected_evidence=(
        "show run confirms ip dhcp excluded-address 10.10.10.1 "
        "10.10.10.250, which excludes 250 of 254 usable addresses in "
        "the /24 pool, consistent with only a small number of leases "
        "succeeding."
    ),
    expected_next_command="show ip dhcp binding to confirm exactly which addresses are currently leased",
    expected_fix=(
        "Narrow the exclusion to only the addresses actually reserved "
        "for static devices, e.g. 'ip dhcp excluded-address 10.10.10.1 "
        "10.10.10.10'"
    ),
    verification_command="show ip dhcp pool VLAN10; ipconfig /renew on a previously-failing PC",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 22. DNS configuration issue - router doing DNS relay misconfigured
# ---------------------------------------------------------------------------
add(
    case_id="DNS-002",
    title="Internal hostname lookups fail company-wide after router swap",
    symptom=(
        "After R2 replaced a failed router, no internal hostnames "
        "resolve anywhere in the company, though external domains like "
        "google.com resolve fine."
    ),
    topology_note=(
        "R2 is configured as a DNS relay ('ip dns server') that forwards "
        "queries to the real internal DNS host, Server1 (10.10.10.53).",
    ),
    show_outputs=(
        "R2# show run | include ip name-server\n"
        "ip name-server 8.8.8.8\n\n"
        "R2# show run | include ip dns server\n"
        "ip dns server\n"
    ),
    expected_fault=(
        "R2's DNS relay is configured with ip name-server 8.8.8.8 only "
        "- the internal authoritative DNS host Server1 (10.10.10.53) "
        "was never added as a name-server, so R2 forwards every query, "
        "including internal-only hostnames, to the public resolver, "
        "which has no record of them."
    ),
    osi_layer="Layer 7",
    concept="DNS",
    severity="Medium",
    expected_evidence=(
        "ip name-server is set only to 8.8.8.8. There is no entry for "
        "10.10.10.53 (Server1, the internal DNS host), which explains "
        "why external names resolve but internal ones do not."
    ),
    expected_next_command="ping 10.10.10.53 from R2 to confirm Server1 itself is reachable",
    expected_fix="ip name-server 10.10.10.53 8.8.8.8",
    verification_command="nslookup an internal hostname from a client PC",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 23. ACL blocking a specific application port (HTTP)
# ---------------------------------------------------------------------------
add(
    case_id="ACL-002",
    title="Intranet web portal unreachable, but file share on same server works",
    symptom=(
        "Users cannot load the intranet web portal at "
        "http://10.10.10.80, but can still access a file share (SMB) "
        "on the exact same server without issue."
    ),
    topology_note=(
        "R1 applies an extended ACL WEB-FILTER inbound on Gi0/0 "
        "(the users' side) intended to block only outbound P2P ports.",
    ),
    show_outputs=(
        "R1# show access-lists WEB-FILTER\n"
        "Extended IP access list WEB-FILTER\n"
        "    10 deny tcp any any eq 80\n"
        "    20 deny tcp any any eq 6881\n"
        "    30 permit ip any any\n\n"
        "R1# show run | section interface Gi0/0\n"
        "interface GigabitEthernet0/0\n"
        " ip access-group WEB-FILTER in\n"
    ),
    expected_fault=(
        "Line 10 of WEB-FILTER denies all TCP port 80 (HTTP) traffic, "
        "which was meant to only block port 6881 (P2P/BitTorrent). "
        "This blocks the intranet portal's HTTP traffic while SMB "
        "(port 445) is unaffected since it isn't matched by either "
        "deny line."
    ),
    osi_layer="Layer 4",
    concept="ACL",
    severity="Medium",
    expected_evidence=(
        "WEB-FILTER line 10 explicitly denies tcp any any eq 80, "
        "applied inbound on the users' interface Gi0/0; SMB (port 445) "
        "is not referenced by the ACL, consistent with file-share "
        "access still working."
    ),
    expected_next_command="show access-lists WEB-FILTER (already conclusive)",
    expected_fix="Remove or renumber the 'deny tcp any any eq 80' line so only port 6881 is denied",
    verification_command="show access-lists WEB-FILTER for hit counters; browse to http://10.10.10.80",
    difficulty="Easy",
)

# ---------------------------------------------------------------------------
# 24. NAT overload issue - overload keyword missing, pool not overloading
# ---------------------------------------------------------------------------
add(
    case_id="NAT-002",
    title="Internet works for a while then stops for everyone",
    symptom=(
        "Internet access works fine in the morning but stops working "
        "for the whole office by early afternoon, and does not recover "
        "until the router is reloaded."
    ),
    topology_note=(
        "R1 uses a NAT pool of 4 public addresses "
        "(203.0.113.10-203.0.113.13) for roughly 60 inside hosts.",
    ),
    show_outputs=(
        "R1# show run | section ip nat pool\n"
        "ip nat pool PUBLIC-POOL 203.0.113.10 203.0.113.13 netmask 255.255.255.252\n"
        "ip nat inside source list 1 pool PUBLIC-POOL\n\n"
        "R1# show ip nat statistics\n"
        "Total active translations: 4 (0 static, 4 dynamic)\n"
        "Pool PUBLIC-POOL: netmask 255.255.255.252\n"
        "  start 203.0.113.10 end 203.0.113.13\n"
        "  type generic, total addresses 4, allocated 4 (100%), misses 812\n"
    ),
    expected_fault=(
        "The NAT pool statement is missing the 'overload' keyword, so "
        "each of the 4 public addresses can only be used for one "
        "inside host's session at a time (one-to-one), not shared via "
        "PAT. With ~60 inside hosts and only 4 addresses, the pool is "
        "exhausted quickly (misses: 812) and new translations fail "
        "until old ones age out."
    ),
    osi_layer="Layer 3",
    concept="NAT",
    severity="High",
    expected_evidence=(
        "show ip nat statistics shows the 4-address pool at 100% "
        "allocation with 812 misses, and the running-config's "
        "'ip nat inside source list 1 pool PUBLIC-POOL' line has no "
        "overload keyword, meaning it cannot multiplex many hosts per "
        "address."
    ),
    expected_next_command="show ip nat translations to confirm many inside hosts are waiting on translations",
    expected_fix="ip nat inside source list 1 pool PUBLIC-POOL overload",
    verification_command="show ip nat statistics; confirm allocated stays healthy under full office load",
    difficulty="Hard",
)

# ---------------------------------------------------------------------------
# 25. Missing NAT inside/outside interface marking
# ---------------------------------------------------------------------------
add(
    case_id="NAT-003",
    title="NAT config looks correct but nothing translates",
    symptom=(
        "PCs on the inside network cannot reach the internet at all. "
        "'show ip nat translations' stays completely empty no matter "
        "how many hosts try to browse."
    ),
    topology_note=(
        "R1 Gi0/0 faces the inside network 192.168.1.0/24; Gi0/1 faces "
        "the ISP.",
    ),
    show_outputs=(
        "R1# show ip nat translations\n"
        "(empty)\n\n"
        "R1# show run | section ip nat|interface Gi\n"
        "interface GigabitEthernet0/0\n"
        " ip address 192.168.1.1 255.255.255.0\n"
        "interface GigabitEthernet0/1\n"
        " ip address 203.0.113.10 255.255.255.252\n"
        "ip nat inside source list 1 interface GigabitEthernet0/1 overload\n"
        "access-list 1 permit 192.168.1.0 0.0.0.255\n"
    ),
    expected_fault=(
        "Neither Gi0/0 nor Gi0/1 has the 'ip nat inside' / 'ip nat "
        "outside' commands applied. The NAT rule, pool, and ACL are all "
        "correctly configured, but without marking the interfaces, the "
        "router never actually performs any translation."
    ),
    osi_layer="Layer 3",
    concept="NAT",
    severity="Critical",
    expected_evidence=(
        "The interface configuration for Gi0/0 and Gi0/1 contains only "
        "IP addressing, with no 'ip nat inside' or 'ip nat outside' "
        "lines, even though the nat source list and ACL rules exist "
        "and are otherwise correct."
    ),
    expected_next_command="show ip nat statistics to confirm zero translations attempted",
    expected_fix=(
        "interface GigabitEthernet0/0; ip nat inside - and - "
        "interface GigabitEthernet0/1; ip nat outside"
    ),
    verification_command="show ip nat translations while a PC browses the internet",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 26. Routing table problem - incorrect next-hop causing a routing loop
# ---------------------------------------------------------------------------
add(
    case_id="ROUTE-003",
    title="Traceroute to remote site shows TTL expiring in a loop",
    symptom=(
        "Traffic to the 172.16.40.0/24 branch network never arrives. "
        "A traceroute shows packets bouncing between two routers "
        "repeatedly before timing out."
    ),
    topology_note=(
        "R1 and R2 are both candidate paths to 172.16.40.0/24, which "
        "physically only exists behind R2 via R2's Gi0/2 "
        "(10.0.12.2 is R1-R2 link on R1 side).",
    ),
    show_outputs=(
        "R1# traceroute 172.16.40.10\n"
        "  1 10.0.12.2  4 msec\n"
        "  2 10.0.12.1  6 msec\n"
        "  3 10.0.12.2  5 msec\n"
        "  4 10.0.12.1  4 msec\n"
        "  (pattern repeats until max TTL)\n\n"
        "R1# show ip route 172.16.40.0\n"
        "Routing entry for 172.16.40.0/24\n"
        "  Known via \"static\", distance 1\n"
        "  Routing Descriptor Blocks:\n"
        "  * 10.0.12.2\n\n"
        "R2# show ip route 172.16.40.0\n"
        "Routing entry for 172.16.40.0/24\n"
        "  Known via \"static\", distance 1\n"
        "  Routing Descriptor Blocks:\n"
        "  * 10.0.12.1\n"
    ),
    expected_fault=(
        "Both R1 and R2 have a static route for 172.16.40.0/24 "
        "pointing at each other (R1 to 10.0.12.2, R2 back to "
        "10.0.12.1), forming a two-hop routing loop. R2's static route "
        "should instead point to its real Gi0/2 next hop toward the "
        "branch, not back to R1."
    ),
    osi_layer="Layer 3",
    concept="Routing",
    severity="High",
    expected_evidence=(
        "traceroute shows the path oscillating between 10.0.12.1 and "
        "10.0.12.2 without progressing; show ip route 172.16.40.0 on "
        "both routers confirms each points the route back at the other."
    ),
    expected_next_command="show ip interface brief on R2 to identify the correct next hop toward 172.16.40.0/24",
    expected_fix="Remove the incorrect static route on R2 and replace with the correct next hop toward the branch (e.g. via Gi0/2)",
    verification_command="traceroute 172.16.40.10 from R1 after the correction",
    difficulty="Hard",
)

# ---------------------------------------------------------------------------
# 27. STP-related issue - redundant link blocked/down disrupting connectivity
# ---------------------------------------------------------------------------
add(
    case_id="STP-001",
    title="Half the building loses connectivity when one switch reboots",
    symptom=(
        "When SW-Core reboots for maintenance, an entire wing of the "
        "building loses connectivity for several minutes even though a "
        "redundant uplink exists.",
    ),
    topology_note=(
        "SW-Access has two uplinks to SW-Core: Gi0/1 (primary) and "
        "Gi0/2 (backup, normally blocking via STP).",
    ),
    show_outputs=(
        "SW-Access# show spanning-tree vlan 10\n"
        "  Interface           Role Sts Cost      Prio.Nbr Type\n"
        "  -------------------- ---- --- --------- -------- --------------------------------\n"
        "  Gi0/1                Root FWD 4         128.1    P2p\n"
        "  Gi0/2                Altn BLK 4         128.2    P2p\n\n"
        "SW-Access# show interfaces gi0/2\n"
        "GigabitEthernet0/2 is up, line protocol is up\n"
    ),
    expected_fault=(
        "This is expected STP behavior under normal conditions - Gi0/2 "
        "is correctly in the Alternate/Blocking role while Gi0/1 is "
        "root/forwarding. The outage during SW-Core's reboot is the "
        "normal STP re-convergence delay (listening/learning states) "
        "before Gi0/2 transitions to forwarding, not a misconfiguration."
    ),
    osi_layer="Layer 2",
    concept="STP",
    severity="Low",
    expected_evidence=(
        "show spanning-tree vlan 10 shows Gi0/2 in role Altn / status "
        "BLK as designed, and show interfaces gi0/2 confirms the "
        "physical link itself is up - the redundant path exists and is "
        "healthy, just temporarily blocking per STP rules."
    ),
    expected_next_command="show spanning-tree vlan 10 detail to check timers (hello/forward-delay) for convergence speed",
    expected_fix=(
        "If faster failover is required, consider enabling PortFast/"
        "UplinkFast equivalents or migrating to Rapid PVST+ (spanning-"
        "tree mode rapid-pvst) to shorten convergence time."
    ),
    verification_command="show spanning-tree vlan 10 during a controlled SW-Core reload to time convergence",
    difficulty="Hard",
)

# ---------------------------------------------------------------------------
# 28. Port security issue - violation shuts the port down
# ---------------------------------------------------------------------------
add(
    case_id="SEC-001",
    title="Employee's laptop loses network after swapping docking stations",
    symptom=(
        "An employee borrowed a coworker's docking station and has had "
        "no network access since, even after switching back to their "
        "own dock. The port's link light is amber/orange."
    ),
    topology_note=(
        "SW1 Fa0/15 has port security configured to allow exactly one "
        "MAC address (the employee's original dock).",
    ),
    show_outputs=(
        "SW1# show port-security interface fa0/15\n"
        "Port Security              : Enabled\n"
        "Port Status                : Secure-shutdown\n"
        "Violation Mode              : Shutdown\n"
        "Maximum MAC Addresses       : 1\n"
        "Total MAC Addresses         : 1\n"
        "Security Violation Count    : 1\n"
        "Last Source Address:Vlan    : 00E0.AAAA.1111:10\n"
    ),
    expected_fault=(
        "Port Fa0/15 is in 'Secure-shutdown' (err-disabled) state after "
        "a port-security violation - a second, different MAC address "
        "(the coworker's dock) appeared on a port allowed only one MAC, "
        "triggering the configured Shutdown violation action. The port "
        "will not recover automatically."
    ),
    osi_layer="Layer 2",
    concept="Port Security",
    severity="Medium",
    expected_evidence=(
        "show port-security interface fa0/15 reports Port Status: "
        "Secure-shutdown and Security Violation Count: 1, with Maximum "
        "MAC Addresses set to 1, confirming a second MAC triggered the "
        "shutdown violation action."
    ),
    expected_next_command="show mac address-table interface fa0/15 to see which MAC is currently secured",
    expected_fix="shutdown then no shutdown on Fa0/15 to clear err-disable (after confirming only the authorized device will reconnect)",
    verification_command="show port-security interface fa0/15; confirm status returns to Secure-up",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 29. Wireless authentication issue - WPA2 PSK mismatch
# ---------------------------------------------------------------------------
add(
    case_id="WIFI-003",
    title="Laptops see the SSID but fail to connect with 'incorrect password'",
    symptom=(
        "Employees can see the CorpWiFi network and attempt to connect "
        "with the passphrase from the IT wiki, but every device reports "
        "an authentication failure.",
    ),
    topology_note=(
        "AP-West broadcasts CorpWiFi with WPA2-PSK security. IT "
        "recently rotated the passphrase as part of a security review.",
    ),
    show_outputs=(
        "AP-West# show running-config | section dot11 ssid CorpWiFi\n"
        "dot11 ssid CorpWiFi\n"
        " vlan 10\n"
        " authentication open\n"
        " authentication key-management wpa version 2\n"
        " wpa-psk ascii 7 105D0F1B48\n"
    ),
    expected_fault=(
        "The AP's WPA2-PSK passphrase (encrypted form shown as "
        "'105D0F1B48') was rotated on the AP, but the IT wiki entry "
        "was not updated at the same time - employees are entering the "
        "old, now-invalid passphrase, causing authentication to fail "
        "for everyone."
    ),
    osi_layer="Layer 2",
    concept="Wireless",
    severity="Medium",
    expected_evidence=(
        "The AP config confirms wpa-psk is actively set (a non-empty "
        "encrypted key), and authentication mode is open/wpa2, ruling "
        "out a broken AP config; the fault pattern (SSID visible, "
        "instant auth failure for all users) is consistent with a "
        "passphrase mismatch versus what users are entering."
    ),
    expected_next_command="Confirm with IT change log whether the passphrase was recently rotated",
    expected_fix="Update the IT wiki/documentation with the new passphrase and redistribute it to staff",
    verification_command="Connect a test laptop with the newly documented passphrase",
    difficulty="Medium",
)

# ---------------------------------------------------------------------------
# 30. Mixed multi-cause case - VLAN mismatch AND missing route together
# ---------------------------------------------------------------------------
add(
    case_id="MIXED-001",
    title="New branch office partially working after go-live",
    symptom=(
        "At the newly opened branch, PCs in the Sales VLAN can reach "
        "the local branch server, but PCs in the Ops VLAN cannot reach "
        "anything outside their own VLAN, including the local server "
        "or HQ."
    ),
    topology_note=(
        "BranchSW has Sales on VLAN 10 and Ops on VLAN 20. BranchR "
        "does router-on-a-stick for both VLANs and connects to HQ over "
        "a WAN link.",
    ),
    show_outputs=(
        "BranchSW# show interfaces fa0/10 switchport\n"
        "Name: Fa0/10\n"
        "Administrative Mode: static access\n"
        "Access Mode VLAN: 20 (Ops)\n\n"
        "BranchR# show ip interface brief\n"
        "Interface                 IP-Address       OK? Method Status  Protocol\n"
        "GigabitEthernet0/0.10     10.20.10.1       YES manual up      up\n"
        "GigabitEthernet0/0.20     10.20.20.1       YES manual up      up\n"
        "Serial0/0/0                192.168.200.1   YES manual up      up\n\n"
        "BranchR# show ip route\n"
        "     10.20.10.0/24 is directly connected, GigabitEthernet0/0.10\n"
        "     10.20.20.0/24 is directly connected, GigabitEthernet0/0.20\n"
        "     192.168.200.0/30 is directly connected, Serial0/0/0\n"
        "     (no route to HQ networks, e.g. 172.16.0.0/16)\n"
    ),
    expected_fault=(
        "Two independent faults are present. (1) Ops VLAN's local "
        "server port issue is not evident here, but Ops (VLAN 20) "
        "traffic leaving the branch has no path to HQ at all: "
        "BranchR's routing table has no route toward HQ's 172.16.0.0/16 "
        "networks, despite the WAN serial link being up. (2) Separately, "
        "Fa0/10's VLAN 20 assignment should be reviewed against the "
        "intended port map, since it governs whether Ops PCs land in "
        "the right subnet in the first place."
    ),
    osi_layer="Layer 3",
    concept="Routing",
    severity="Critical",
    expected_evidence=(
        "show ip route on BranchR lists only directly connected "
        "networks and the serial link - no route to HQ's 172.16.0.0/16 "
        "exists even though Serial0/0/0 (192.168.200.1) is up/up, which "
        "explains why nothing beyond the local VLANs is reachable for "
        "any branch VLAN, not just Ops."
    ),
    expected_next_command="show ip route on the HQ-side router to confirm what return route/summarization is expected",
    expected_fix=(
        "Add the missing route toward HQ, e.g. 'ip route 172.16.0.0 "
        "255.255.0.0 192.168.200.2' (or enable the intended dynamic "
        "routing protocol on the WAN link), then separately confirm "
        "Fa0/10's VLAN assignment matches the port map."
    ),
    verification_command="show ip route on BranchR; ping an HQ host from both Sales and Ops VLANs",
    difficulty="Hard",
)


def main():
    out_path = os.path.join(os.path.dirname(__file__), "cases.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in CASES:
            # topology_note was sometimes accidentally passed as a 1-tuple
            # via a trailing comma in a triple-quoted string; normalize.
            for k, v in row.items():
                if isinstance(v, tuple):
                    row[k] = v[0]
            writer.writerow(row)
    print(f"Wrote {len(CASES)} cases to {out_path}")


if __name__ == "__main__":
    main()
