"""
Populates data/ai_results.json with diagnoses written directly by Claude
(in this chat), as a free substitute for running scripts/run_diagnosis.py
with a paid API key. Same JSON schema, same underlying model.
"""
import json
import os

RESULTS = {
"C001": {
    "root_cause": "VLAN 20 is not permitted on the SW1-R1 trunk, so tagged traffic for VLAN 20 never reaches the router's sub-interface.",
    "confidence": "high",
    "evidence": "show interfaces trunk lists 'Allowed VLANs on trunk: 1,10' — VLAN 20 is absent even though VLAN 20 exists and is active in show vlan brief.",
    "osi_layer": "Layer 2",
    "next_command": "show running-config interface gi0/1",
    "fix_steps": [
        "On SW1, enter interface configuration mode for Gi0/1 (the trunk port to R1).",
        "Run 'switchport trunk allowed vlan add 20'.",
        "Verify with 'show interfaces trunk' that VLAN 20 now appears in the allowed list.",
        "Re-test connectivity from PC-A to PC-B."
    ]
},
"C002": {
    "root_cause": "VLAN 30 no longer exists in the switch's VLAN database, so Fa0/5 (statically assigned to VLAN 30) is inactive.",
    "confidence": "high",
    "evidence": "show vlan brief lists only VLAN 1 and VLAN 10; VLAN 30 is missing. show interfaces fa0/5 switchport confirms 'Access Mode VLAN: 30 (Inactive)'.",
    "osi_layer": "Layer 2",
    "next_command": "show vlan brief",
    "fix_steps": [
        "Re-create VLAN 30 with 'vlan 30' then 'name Finance'.",
        "Confirm Fa0/5 shows 'Access Mode VLAN: 30' as active (not inactive) afterward.",
        "Re-test connectivity for the hosts on Fa0/5.",
        "If VLAN 30 was intentionally removed, confirm with the team before re-creating it."
    ]
},
"C003": {
    "root_cause": "FastEthernet0/8 is administratively shut down, likely left over from decommissioning the previous printer.",
    "confidence": "high",
    "evidence": "'show interfaces fa0/8' reports 'is administratively down, line protocol is down'.",
    "osi_layer": "Layer 1",
    "next_command": "show running-config interface fa0/8",
    "fix_steps": [
        "Enter interface configuration mode for Fa0/8.",
        "Run 'no shutdown'.",
        "Confirm the correct VLAN is assigned for the new PC's intended network.",
        "Verify the port shows 'up, up' and the PC obtains an IP address."
    ]
},
"C004": {
    "root_cause": "The port's data VLAN is still at the default VLAN 1 instead of VLAN 10, so PCs behind the phone land on the wrong (default) VLAN.",
    "confidence": "high",
    "evidence": "'show interfaces fa0/2 switchport' shows 'Access Mode VLAN: 1 (default)' while 'Voice VLAN: 110 (Active)' is correctly set.",
    "osi_layer": "Layer 2",
    "next_command": "show running-config interface fa0/2",
    "fix_steps": [
        "Enter interface configuration mode for Fa0/2.",
        "Run 'switchport access vlan 10' to set the correct data VLAN.",
        "Leave the voice VLAN configuration (110) untouched.",
        "Verify with 'show interfaces fa0/2 switchport' and re-test PC connectivity."
    ]
},
"C005": {
    "root_cause": "The native VLAN differs between the two switches on the shared trunk (SW1=1, SW2=99), which mishandles untagged traffic and can disrupt VLAN 40 communication between the switches.",
    "confidence": "medium",
    "evidence": "SW1's trunk shows 'Native vlan 1' and SW2's shows 'Native vlan 99' on the same Gi0/1-Gi0/1 link, with identical allowed VLANs (1,10,20,40) otherwise.",
    "osi_layer": "Layer 2",
    "next_command": "show interfaces gi0/1 switchport",
    "fix_steps": [
        "Decide on one native VLAN for this trunk (commonly VLAN 1, or a dedicated unused VLAN per your security policy).",
        "On whichever switch is mismatched, run 'switchport trunk native vlan <chosen-id>' under the Gi0/1 interface.",
        "Confirm both sides now report the same native VLAN with 'show interfaces trunk'.",
        "Re-test VLAN 40 connectivity between hosts on SW1 and SW2."
    ]
},
"C006": {
    "root_cause": "PC-A's configured default gateway (192.168.10.254) does not match R1's actual sub-interface IP (192.168.10.1), so all off-subnet traffic is sent to a non-existent gateway.",
    "confidence": "high",
    "evidence": "PC-A's ipconfig shows 'Default Gateway: 192.168.10.254', while R1's Gi0/0.10 is actually 192.168.10.1 (up/up).",
    "osi_layer": "Layer 3",
    "next_command": "ipconfig /all",
    "fix_steps": [
        "On PC-A, update the default gateway to 192.168.10.1 (matching R1's Gi0/0.10).",
        "If PC-A uses DHCP, check the DHCP pool's default-router setting instead of the static config.",
        "Re-test 'ping 192.168.10.1' and then a destination outside the subnet.",
        "Check other PCs on the same VLAN for the same misconfiguration."
    ]
},
"C007": {
    "root_cause": "The WAN-facing interface Gi0/1 on R1 is administratively shut down, so there is no path beyond the local gateway.",
    "confidence": "high",
    "evidence": "'show ip interface brief' on R1 shows Gi0/1 status as 'administratively down' with protocol 'down', while Gi0/0 (LAN side) is up/up.",
    "osi_layer": "Layer 1",
    "next_command": "show running-config interface gi0/1",
    "fix_steps": [
        "Enter interface configuration mode for Gi0/1 on R1.",
        "Run 'no shutdown'.",
        "Verify 'show ip interface brief' now shows Gi0/1 as up/up.",
        "Re-test connectivity beyond the gateway."
    ]
},
"C008": {
    "root_cause": "Based on the evidence given, this does not look like a fault — spanning tree is correctly blocking the redundant Gi0/2 path on SW1 (Role Altn, State BLK) to prevent a loop, which is expected behavior on a redundant link.",
    "confidence": "medium",
    "evidence": "SW1's 'show spanning-tree vlan 10' shows Gi0/1 as Root/FWD and Gi0/2 as Altn/BLK — a healthy, intentional STP topology, not a failure.",
    "osi_layer": "Layer 2",
    "next_command": "show vlan brief",
    "fix_steps": [
        "Do not disable STP or force Gi0/2 to forwarding — that would risk a loop.",
        "Instead check VLAN 10 access-port assignment on the specific PCs that cannot reach the gateway.",
        "Check cabling and interface status on the affected hosts' individual switchports.",
        "If half the PCs are on SW2 behind the blocked Gi0/2, note that blocking is normal; investigate PC-side config or the port each failing PC is on."
    ]
},
"C009": {
    "root_cause": "A duplex mismatch is likely occurring on Fa0/1 — the switch port is set to full-duplex but the PC's NIC may still be negotiating half-duplex, producing late collisions.",
    "confidence": "medium",
    "evidence": "'show interfaces fa0/1' shows 'Full-duplex, 100Mb/s' on the switch side along with 'late collision: 4210', a classic duplex-mismatch signature (late collisions don't occur in true full-duplex operation).",
    "osi_layer": "Layer 1",
    "next_command": "show interfaces fa0/1 | include duplex",
    "fix_steps": [
        "Check the PC's NIC duplex/speed setting; ideally set both ends to 'auto' or match them explicitly.",
        "If forcing manually, set the switchport to match the PC's setting exactly (both full or both half).",
        "Clear interface counters and re-check for late collisions after the change.",
        "Re-test 'ping gateway' for consistency."
    ]
},
"C010": {
    "root_cause": "The VLAN 20 sub-interface on R1 has no 'ip helper-address' configured, so DHCP broadcast requests are never relayed to the remote DHCP server on VLAN 99.",
    "confidence": "high",
    "evidence": "'show run interface gi0/0.20' shows the IP address configured but explicitly notes 'no ip helper-address configured'.",
    "osi_layer": "Layer 3",
    "next_command": "show running-config interface gi0/0.20",
    "fix_steps": [
        "Enter interface configuration mode for Gi0/0.20 on R1.",
        "Run 'ip helper-address <DHCP-server-IP>' pointing to the server on VLAN 99.",
        "Repeat for any other VLAN sub-interfaces that rely on the same remote DHCP server.",
        "On an affected PC, release/renew its IP and confirm it now receives a real address instead of an APIPA (169.254.x.x) one."
    ]
},
"C011": {
    "root_cause": "The DHCP pool for VLAN 30 is configured with a /29 mask (255.255.255.248), giving only 6 usable addresses, instead of the intended /24.",
    "confidence": "high",
    "evidence": "'ip dhcp pool VLAN30' shows 'network 192.168.30.0 255.255.255.248', which is a /29, far smaller than a typical /24 LAN.",
    "osi_layer": "Layer 3",
    "next_command": "show ip dhcp pool VLAN30",
    "fix_steps": [
        "Enter the DHCP pool configuration for VLAN30.",
        "Change the network statement to 'network 192.168.30.0 255.255.255.0'.",
        "If any of the 6 addresses were already leased to devices outside the intended range, verify no conflicts occur.",
        "Confirm with 'show ip dhcp pool VLAN30' and re-test additional PCs receiving addresses."
    ]
},
"C012": {
    "root_cause": "PC-B's current address (192.168.40.20) falls inside the router's excluded-address range (192.168.40.1–192.168.40.50), so the DHCP server can never legitimately renew or reassign this address to it.",
    "confidence": "medium",
    "evidence": "'ip dhcp excluded-address 192.168.40.1 192.168.40.50' on R1, while PC-B's ipconfig shows an address of 192.168.40.20, inside that excluded range.",
    "osi_layer": "Layer 3",
    "next_command": "show ip dhcp binding",
    "fix_steps": [
        "Check if PC-B is configured with a static IP (likely, since DHCP couldn't have issued this address).",
        "If DHCP was intended, remove the static configuration on PC-B and release/renew to get a real DHCP lease outside the excluded range.",
        "If the address was meant to be reserved for PC-B, add an explicit DHCP host reservation for it instead of relying on the excluded range.",
        "Re-confirm the excluded-address range doesn't conflict with other reserved devices."
    ]
},
"C013": {
    "root_cause": "Fa0/9 has been placed into an err-disabled state by BPDU Guard, most likely because the unmanaged switch connected there introduced a loop or forwarded a BPDU, which PortFast+BPDU Guard treats as a violation.",
    "confidence": "high",
    "evidence": "'show interfaces fa0/9' reports 'up, line protocol is up (err-disabled)' along with the log line '%PM-4-ERR_DISABLE: portfast-bpduguard error detected on Fa0/9'.",
    "osi_layer": "Layer 2",
    "next_command": "show interfaces status err-disabled",
    "fix_steps": [
        "Identify and remove the unmanaged switch causing the loop, or confirm it is safe to reconnect without looping back into the network.",
        "Re-enable the port with 'shutdown' then 'no shutdown' on Fa0/9 (or wait for err-disable recovery timeout if configured).",
        "Confirm BPDU Guard and PortFast are appropriate for this access port going forward.",
        "Re-test the laptop's connectivity once the port is up again."
    ]
},
"C014": {
    "root_cause": "PC-A is configured to use its default gateway (192.168.10.1) as its DNS server, not the actual internal DNS server (192.168.99.10), and the router does not appear to relay DNS requests, so name resolution fails.",
    "confidence": "high",
    "evidence": "PC-A's ipconfig /all shows 'DNS Servers: 192.168.10.1', which matches its Default Gateway, not the stated internal DNS server address of 192.168.99.10.",
    "osi_layer": "Layer 7",
    "next_command": "nslookup www.netsage.local",
    "fix_steps": [
        "Update PC-A's DNS server setting to 192.168.99.10 (directly, or via the DHCP pool's dns-server option if using DHCP).",
        "If other PCs are affected, check the DHCP pool configuration for the wrong DNS server value.",
        "Re-test 'ping www.netsage.local' to confirm resolution succeeds.",
        "Confirm no other PCs are relying on the incorrect DNS setting."
    ]
},
"C015": {
    "root_cause": "The internal DNS server has no forwarder configured for queries it cannot answer authoritatively, so external domain lookups have nowhere to go.",
    "confidence": "high",
    "evidence": "'show run | include forwarder' on the DNS server explicitly returns 'no forwarders configured'.",
    "osi_layer": "Layer 7",
    "next_command": "show run | include forwarder",
    "fix_steps": [
        "Configure a forwarder on the DNS server pointing to a reachable upstream DNS resolver (e.g. your ISP's DNS or a public resolver like 8.8.8.8).",
        "Verify the DNS server can reach that upstream address (check routing/firewall rules).",
        "Re-test resolving an external domain from a client PC.",
        "Confirm internal name resolution still works unaffected."
    ]
},
"C016": {
    "root_cause": "There are two conflicting A records for the same hostname (www.netsage.local) on the DNS server, so different clients resolve to different IPs depending on which record is returned/cached.",
    "confidence": "high",
    "evidence": "'show host www.netsage.local' returns two separate A records: 192.168.50.10 and 192.168.50.99.",
    "osi_layer": "Layer 7",
    "next_command": "show host www.netsage.local",
    "fix_steps": [
        "Determine which IP address is the correct/current one for this service.",
        "Remove the incorrect duplicate A record from the DNS server.",
        "Flush DNS caches on affected clients if resolution still appears stale.",
        "Re-test that all clients now consistently resolve to the single correct address."
    ]
},
"C017": {
    "root_cause": "ACL 101 on R1 explicitly denies UDP port 53 (DNS) before its permit-any statement, blocking all DNS traffic network-wide.",
    "confidence": "high",
    "evidence": "'show access-lists 101' shows line 10 as 'deny udp any any eq 53' ahead of line 20 'permit ip any any' — the deny is matched first for all DNS traffic.",
    "osi_layer": "Layer 4",
    "next_command": "show ip interface | include access list",
    "fix_steps": [
        "Confirm which interface ACL 101 is applied to and whether blocking DNS was intentional.",
        "If not intended, remove or modify the 'deny udp any any eq 53' line (or add a permit above it for the specific required DNS traffic).",
        "Re-apply/verify the ACL and re-test DNS resolution from a client on each affected VLAN.",
        "Document the change, since this was likely part of a hardening effort that had an unintended side effect."
    ]
},
"C018": {
    "root_cause": "R1 has no route to 192.168.30.0/24 in its routing table, even though the PC can reach its own gateway, meaning the VLAN 30 sub-interface may be down or was never brought fully up.",
    "confidence": "medium",
    "evidence": "'show ip route' on R1 shows 192.168.10.0/24 as directly connected, but the evidence explicitly notes the 192.168.30.0/24 route is missing.",
    "osi_layer": "Layer 3",
    "next_command": "show ip interface brief",
    "fix_steps": [
        "Check the status of R1's VLAN 30 sub-interface (e.g. Gi0/0.30) with 'show ip interface brief' — directly connected routes only appear when the interface is up/up.",
        "If the sub-interface is down, bring it up with 'no shutdown' and confirm encapsulation/VLAN ID are correct.",
        "If the interface is already up, verify the IP address is correctly assigned.",
        "Re-check 'show ip route' for the 192.168.30.0/24 entry and re-test connectivity."
    ]
},
"C019": {
    "root_cause": "R2's static route to 10.10.0.0/16 points to a next hop (192.168.100.2) that does not match R1's actual serial interface address, so the route is unusable even though it's in the routing table.",
    "confidence": "medium",
    "evidence": "R2's static route uses next-hop 192.168.100.2, but R2's own serial interface is 192.168.100.1 — the evidence notes 192.168.100.2 appears not to be directly reachable on this point-to-point link.",
    "osi_layer": "Layer 3",
    "next_command": "show ip route static",
    "fix_steps": [
        "Confirm R1's actual serial interface IP address on the shared link with R2.",
        "Correct the static route on R2 to use R1's real interface IP as the next hop (likely a typo in the current configuration).",
        "Verify the route now resolves correctly and appears as a valid path in 'show ip route'.",
        "Re-test reachability to the 10.10.0.0/16 HQ subnet from R2."
    ]
},
"C020": {
    "root_cause": "R1 and R2 have mismatched MTU settings (1500 vs 1400) on their shared OSPF interface, which prevents Database Description packet exchange and keeps the neighbor relationship stuck.",
    "confidence": "high",
    "evidence": "R1's Gi0/1 shows 'MTU 1500' while R2's Gi0/1 shows 'MTU 1400' for the same OSPF Area 0 adjacency.",
    "osi_layer": "Layer 3",
    "next_command": "show ip ospf neighbor",
    "fix_steps": [
        "Decide on a consistent MTU for this link (commonly matching the default, 1500, unless there's a specific reason for 1400).",
        "Adjust the mismatched interface's MTU to match the other side.",
        "Alternatively, if the MTU difference is intentional, configure 'ip ospf mtu-ignore' on both interfaces as a workaround.",
        "Confirm the OSPF neighbor state reaches 'Full' afterward."
    ]
},
"C021": {
    "root_cause": "The server-side router's static return route to the PC's subnet (192.168.10.0/24) points to a next hop (192.168.200.9) that is not directly reachable, causing asymmetric/broken return routing.",
    "confidence": "medium",
    "evidence": "'show ip route 192.168.10.0' on SRV-R shows the static route via 192.168.200.9, and the evidence notes this next hop is unreachable/not directly connected.",
    "osi_layer": "Layer 3",
    "next_command": "show ip route",
    "fix_steps": [
        "Identify the correct, directly-reachable next hop for reaching the PC's subnet from this router.",
        "Correct the static route to use that valid next hop (or remove it in favor of a dynamic routing protocol if appropriate).",
        "Verify the corrected route appears as reachable in the routing table.",
        "Re-test the full round-trip path between the PC and the server."
    ]
},
"C022": {
    "root_cause": "The 192.168.60.0/24 subnet was never added to R1's RIP 'network' statements, so RIP never advertises it to R2 even though R1 can reach it directly.",
    "confidence": "high",
    "evidence": "R1's RIP configuration lists 'network 192.168.10.0' and 'network 192.168.30.0', with the evidence explicitly noting 192.168.60.0 is not included.",
    "osi_layer": "Layer 3",
    "next_command": "show ip protocols",
    "fix_steps": [
        "Enter RIP router configuration mode on R1.",
        "Add 'network 192.168.60.0' to include the new subnet in RIP advertisements.",
        "Verify with 'show ip route rip' on R2 that the route now appears.",
        "Re-test reachability to 192.168.60.0/24 from R2's side."
    ]
},
"C023": {
    "root_cause": "ACL 110, applied inbound on Gi0/0.30, explicitly denies the entire 192.168.10.0/24 subnet before its permit-any statement, blocking VLAN 10's access to the VLAN 30 server.",
    "confidence": "high",
    "evidence": "'show access-lists 110' line 10 is 'deny ip 192.168.10.0 0.0.0.255 any', confirmed as the inbound ACL on Gi0/0.30 via 'show ip interface gi0/0.30'.",
    "osi_layer": "Layer 3/4",
    "next_command": "show access-lists 110",
    "fix_steps": [
        "Confirm with the team whether blocking VLAN 10 from this server is intentional.",
        "If not intended, add a permit statement for the required VLAN 10 traffic above the deny line, or remove the deny line if it's a blanket mistake.",
        "Re-apply and verify the ACL with 'show ip interface gi0/0.30'.",
        "Re-test connectivity and document the change if the original ACL intent was unclear."
    ]
},
"C024": {
    "root_cause": "The VTY lines are configured with 'transport input telnet' only, which explicitly limits remote access to Telnet and excludes SSH.",
    "confidence": "high",
    "evidence": "'show run | section line vty' shows 'transport input telnet' with no mention of ssh, alongside an access-class restricting source IPs (which is unrelated to the protocol restriction).",
    "osi_layer": "Layer 7",
    "next_command": "show run | section line vty",
    "fix_steps": [
        "Enter VTY line configuration mode (line vty 0 4).",
        "Run 'transport input ssh' (or 'transport input ssh telnet' if Telnet access still needs to remain available, though SSH-only is more secure).",
        "Confirm SSH keys/credentials are properly configured on the router if not already.",
        "Re-test SSH access from the management PC."
    ]
},
"C025": {
    "root_cause": "Standard ACL 10 was applied on the data interface Gi0/0 instead of the VTY lines, so it filters ALL IP traffic from 192.168.10.5, not just Telnet sessions as intended.",
    "confidence": "high",
    "evidence": "'ip access-group 10 in' is applied under 'interface GigabitEthernet0/0', and ACL 10 is a standard ACL that matches only on source IP with no protocol/port specificity.",
    "osi_layer": "Layer 3",
    "next_command": "show ip interface gi0/0 | include access list",
    "fix_steps": [
        "Remove 'ip access-group 10 in' from interface Gi0/0.",
        "Apply the same ACL as an 'access-class 10 in' under the VTY lines instead, which correctly scopes it to remote-access sessions only.",
        "Verify Gi0/0 now shows no inbound access list, and that VTY lines show the access-class applied.",
        "Re-test that 192.168.10.5 has normal data connectivity, and that Telnet access is still appropriately restricted."
    ]
},
"C026": {
    "root_cause": "The named ACL GUEST-WEB-ONLY exists and is correctly written, but it was never applied to any interface, so it has no actual filtering effect.",
    "confidence": "high",
    "evidence": "'show ip interface gi0/0.50' reports both 'Inbound access list is not set' and 'Outbound access list is not set', while the ACL itself exists with the intended permit statements.",
    "osi_layer": "Layer 3/4",
    "next_command": "show ip interface gi0/0.50",
    "fix_steps": [
        "Enter interface configuration mode for Gi0/0.50 (the guest VLAN sub-interface).",
        "Apply the ACL with 'ip access-group GUEST-WEB-ONLY in' (or 'out', depending on intended direction).",
        "Verify with 'show ip interface gi0/0.50' that the ACL is now listed as applied.",
        "Re-test that guest traffic is now correctly restricted to HTTP/HTTPS only."
    ]
},
"C027": {
    "root_cause": "'ip nat inside' was never configured on the LAN-facing interface Gi0/0, so R1 never recognizes traffic from internal hosts as needing translation.",
    "confidence": "high",
    "evidence": "'show run | section ip nat' shows the NAT overload rule and 'ip nat outside' correctly applied to Gi0/1, but explicitly notes 'ip nat inside missing' under Gi0/0.",
    "osi_layer": "Layer 3",
    "next_command": "show ip nat translations",
    "fix_steps": [
        "Enter interface configuration mode for Gi0/0 (the internal LAN interface).",
        "Run 'ip nat inside'.",
        "Verify with 'show ip nat statistics' or by generating traffic and checking 'show ip nat translations' that translations now appear.",
        "Re-test internet access from an internal PC."
    ]
},
"C028": {
    "root_cause": "The NAT source access-list (ACL 1) does not include the newly added VLAN 40 subnet, so traffic from VLAN 40 is never matched for translation.",
    "confidence": "high",
    "evidence": "'show access-lists 1' shows only 'permit 192.168.10.0 0.0.0.255', with the evidence noting 192.168.40.0/24 is not included.",
    "osi_layer": "Layer 3",
    "next_command": "show access-lists 1",
    "fix_steps": [
        "Add a permit line to ACL 1 for the VLAN 40 subnet: 'access-list 1 permit 192.168.40.0 0.0.0.255'.",
        "Confirm the NAT configuration ('ip nat inside source list 1 ...') still references this same ACL number.",
        "Verify with 'show ip nat translations' that VLAN 40 traffic now gets translated.",
        "Re-test internet access from a VLAN 40 host."
    ]
},
"C029": {
    "root_cause": "Inbound ACL 101 on the outside interface denies TCP port 80 before the static NAT translation for the web server can take effect, so the packets are dropped before NAT is even evaluated for return traffic.",
    "confidence": "medium",
    "evidence": "'show access-lists 101' shows 'deny tcp any any eq 80' as line 10, ahead of 'permit ip any any' — and this ACL is on the same router where the static NAT rule for port 80 exists.",
    "osi_layer": "Layer 4",
    "next_command": "show ip interface | include access list",
    "fix_steps": [
        "Confirm ACL 101 is applied inbound on the outside (internet-facing) interface.",
        "Add a specific permit line above the deny for the static NAT's public IP/port (203.0.113.10 TCP/80), or otherwise adjust ordering so legitimate forwarded traffic isn't blocked.",
        "Re-apply/verify the ACL and re-test reaching the web server from outside.",
        "Double check no other required services were also inadvertently blocked by the same deny-before-permit pattern."
    ]
},
"C030": {
    "root_cause": "No isolation ACL is applied on the Guest VLAN 50 sub-interface, so guest Wi-Fi traffic is not restricted from reaching internal subnets.",
    "confidence": "high",
    "evidence": "'show ip interface gi0/0.50' reports 'Inbound access list is not set', confirming no filtering is currently applied to guest traffic on this interface.",
    "osi_layer": "Layer 3",
    "next_command": "show ip interface gi0/0.50",
    "fix_steps": [
        "Write an ACL that denies traffic from 192.168.50.0/24 (or the guest subnet) to internal subnets, while permitting internet-bound traffic.",
        "Apply it inbound on Gi0/0.50 with 'ip access-group <name> in'.",
        "Verify the ACL is applied with 'show ip interface gi0/0.50'.",
        "Re-test that guest devices can still reach the internet but not internal file servers."
    ]
},
"C031": {
    "root_cause": "There is a RADIUS shared-secret mismatch for at least some clients/policies, causing authentication failures for the affected laptops on the WPA2-Enterprise SSID.",
    "confidence": "medium",
    "evidence": "The RADIUS server log explicitly shows 'AUTH FAIL: shared secret mismatch from 192.168.1.5', and the AP's configured key ('CorpKey123') would need to exactly match what's configured on the RADIUS server.",
    "osi_layer": "Layer 2",
    "next_command": "show run | include radius",
    "fix_steps": [
        "Compare the shared secret configured on the AP/WLC against the one configured for that NAS/client entry on the RADIUS server.",
        "Correct whichever side has the mismatched key so both match exactly.",
        "Restart or re-test authentication from a previously-failing laptop.",
        "Check whether other NAS/AP entries on the RADIUS server have the same inconsistency if this was a recent bulk change."
    ]
},
"C032": {
    "root_cause": "AP1 and AP2 are both configured on the same wireless channel (6) in overlapping coverage areas, causing co-channel interference and frequent disconnects at the coverage edge.",
    "confidence": "high",
    "evidence": "Both 'show controllers dot11radio 0' outputs report 'Channel: 6' for AP1 and AP2, which are described as having overlapping coverage.",
    "osi_layer": "Layer 1",
    "next_command": "show controllers dot11radio 0",
    "fix_steps": [
        "Change one AP to a non-overlapping channel relative to the other (e.g. channels 1, 6, 11 for 2.4GHz — pick a different one of these three).",
        "If using 5GHz, select non-overlapping channels appropriate for that band instead.",
        "Verify the new channel assignment with 'show controllers dot11radio 0' on the changed AP.",
        "Monitor client behavior near the coverage boundary to confirm reduced disconnects."
    ]
},
}

def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_path = os.path.join(base, "data", "ai_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2)
    print(f"Wrote {len(RESULTS)} AI diagnoses to {out_path}")

if __name__ == "__main__":
    main()
