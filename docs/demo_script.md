# NetSage AI - Demo Script (5–10 minutes)

Suggested case for the walkthrough: **`INTERVLAN-001`** (VLAN 30 can
ping its gateway but not a VLAN 10 server - a clean, single-cause,
high-confidence case that demonstrates the full pipeline well). A
second case, **`STP-001`**, is suggested at the end for the "human
catches a bad AI suggestion" beat, since its scripted mock diagnosis
recommends something a reviewer should reject.

No API key is required - the entire demo runs in mock mode.

---

### 0:00–1:00 - Problem introduction

> "Junior network engineers often know individual Cisco commands but
> struggle to connect a symptom to the actual root cause. A PC that
> gets an IP but can't reach a server could be a VLAN issue, a routing
> issue, an ACL, NAT, a dozen other things. NetSage AI helps a student
> move from symptom, to evidence, to a hypothesis - while keeping a
> human in charge of every decision."

Open the dashboard (`/`) and point at the safety banner:

> "That's not a footnote - it's enforced in the code at four or five
> different layers, which I'll show later."

### 1:00–2:00 - Show architecture

Open `docs/architecture.md` or just narrate the pipeline:

> "Every case goes through two independent, parallel checks: a
> deterministic rule checker - plain regex, no AI, same input always
> gives the same output - and an AI diagnosis. Neither one can act on
> its own. Both go to a human, who accepts, edits, or rejects."

### 2:00–4:00 - Open a broken networking case

Navigate to `/cases`, search or filter to `INTERVLAN-001`, open it.

Walk through:
- The symptom ("PC in VLAN 30 can ping its gateway but not a VLAN 10
  server")
- The topology note
- Expand the show-command output block - point out it's real,
  plausible Cisco IOS output, not placeholder text.

### 4:00–5:00 - Run the rule checker

Click "Run checks."

> "This step never calls an LLM. It's just pattern matching against the
> show output - you can read every check in `backend/rules/`. For this
> particular case it comes back empty, which is honest: this fault
> (a subinterface missing its IP address) isn't something the current
> rule set catches deterministically. That's exactly the kind of gap
> the AI layer is meant to help with."

(Optional aside: switch to `IFACE-001` or `TRUNK-001` briefly to show a
case where the rule checker *does* fire, if you want to demonstrate a
non-empty result before returning to `INTERVLAN-001`.)

### 5:00–6:00 - Run the AI diagnosis

Click "Request AI diagnosis." Point out the mock-mode notice.

> "No API key is configured right now, so this is running in
> deterministic demo mode - same case always produces the same
> response, which matters for a live demo. With a real
> GEMINI_API_KEY set, this exact same button calls the live Gemini
> API instead; nothing else in the app changes. If a model's quota
> runs out mid-demo, it automatically retries the next model in the
> fallback chain instead of failing - you'd see that as a small badge
> saying which model actually answered."

### 6:00–7:00 - Show the evidence-backed recommendation

Walk through the AI Diagnosis card:
- Root cause
- Confidence label and percentage
- The **evidence** list - emphasize these are facts pulled from the
  actual show output, not invented
- The reasoning summary
- Suggested fix steps and verification steps

> "Notice what's missing: an 'Apply fix' button. There isn't one,
> anywhere in this app. The only thing that happens next is a human
> decision."

### 7:00–8:00 - Human reviewer rejects/edits a diagnosis

Switch to **`STP-001`**. Run the checker (empty - a blocking redundant
port isn't a fault), then request an AI diagnosis. The scripted mock
response recommends disabling spanning-tree on the blocking port.

> "This is deliberately a bad recommendation - Gi0/2 being in a
> blocking state is normal, healthy STP behavior. Disabling
> spanning-tree there would introduce a loop risk. A reviewer needs to
> catch this."

Click **Reject**, type a reason (e.g. "This is expected STP behavior,
not a fault - disabling STP here would risk a bridging loop"), submit.

### 8:00–9:00 - Show the corrected diagnosis and verification

> "That decision is now permanently in the Responsible AI log -
> `data/reviews.csv` - with the reason attached. It's not silently
> discarded; you can see it on the dashboard's 'Recent reviews' list
> and in the agreement-rate statistic, which counts rejections against
> the AI rather than hiding them."

Scroll to the Verification section for the accepted case
(`INTERVLAN-001`, if you accepted it earlier) to show the
`verification_command`.

### 9:00–10:00 - Dashboard and Responsible AI statistics

Return to `/`. Walk through:
- Total cases / Reviewed / AI agreement / Corrections cards
- Cases by concept, severity, OSI layer charts
- Accepted vs Edited vs Rejected pie chart
- The AI vs human agreement ring
- Rule-checker findings bar chart
- Recent reviews list (should now include your STP-001 rejection)

Close with:

> "The dataset ships with 12 pre-existing reviews, including several
> where the AI was wrong or was recommending something actively unsafe.
> That's the point - not that the AI is bad, but that a deterministic
> checker plus a human reviewer catches things a standalone model
> wouldn't."

---

## Fast path (if short on time)

If you only have 3–4 minutes: dashboard safety banner (15s) →
`INTERVLAN-001` full pipeline through Accept (2 min) → `STP-001`
diagnosis + Reject with reason (1 min) → back to dashboard, point at
the updated agreement rate and recent reviews (30s).

## Resetting between demo runs

Reviews accumulate in `data/reviews.csv` as you submit them during a
demo. To reset back to the shipped 12-case seed history before a
re-run:

```bash
cd data
python3 generate_reviews.py
```

This is safe to run at any time - it fully regenerates the file and
does not touch `cases.csv`.
