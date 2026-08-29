# Additional Worked Examples

These supplement the three worked examples embedded directly in
`diagnose_prompt.md`. They're used in `docs/demo_script.md` and are
handy for manual testing of the AI client in mock mode.

## Example A - Evidence contradicts the obvious symptom-based guess

**Case:** `DNS-001`

A student might instinctively guess "DNS server is misconfigured on the
router" just from the symptom description. But the supplied evidence
(`ipconfig /all` on the client, plus the DHCP pool config) shows the
*client* is receiving the wrong `dns-server` value from DHCP - a
different, more specific, and more fixable root cause than "the DNS
server is broken."

This is exactly the kind of case NetSage AI is designed to help with:
turning "something about DNS is wrong" into an evidence-backed,
actionable finding.

## Example B - When the AI should recommend a next command instead of guessing

**Case:** `MASK-001` (partial evidence variant)

If only PC-D's `ipconfig` output is available (no peer PC, no switch
output), the correct AI behavior is **not** to confidently declare a
subnet mask mismatch. The right move is:

```json
"confidence_label": "Low",
"next_command": "ipconfig on a working peer PC on the same switch, plus show interfaces switchport for both PCs' ports"
```

Only once a peer's configuration is supplied (showing a different mask
on the same segment) should confidence rise to High.

## Example C - A "fix" that is actually working-as-designed

**Case:** `STP-001` / `WIFI-002`

Not every anomaly is a misconfiguration. `STP-001`'s blocking port and
`WIFI-002`'s client isolation are both *intentional* states. NetSage AI
should recognize when the evidence describes expected behavior and
frame the finding as a design/policy question for a human, rather than
inventing a "fix" that would actually reduce safety (e.g. disabling STP
on a redundant link) or undermine an intentional security control.

This is also why `REV-0011` in `data/reviews.csv` shows a case where a
human reviewer **rejected** an AI suggestion that would have introduced
a bridging loop risk - a concrete illustration of why mandatory human
review matters, not just as a formality.
