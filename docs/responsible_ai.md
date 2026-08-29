# Responsible AI in NetSage AI

## The core principle

**AI recommendations are suggestions and must be reviewed by a human
before implementation.** NetSage AI is a troubleshooting *assistant*,
not an autonomous network administrator. It never applies a
configuration change to any device, real or simulated.

This isn't just a statement in the README - it's enforced at multiple
layers so that no single bug or oversight can turn it into a false
promise.

## Where this is enforced in code

1. **The AI is explicitly instructed** to always set
   `human_review_required: true` in its structured output
   (`prompts/diagnose_prompt.md`, `backend/ai/diagnosis.py::SYSTEM_PROMPT`).

2. **The field is force-overwritten server-side regardless of what the
   model returns.** `backend/ai/schemas.py::AIDiagnosis._force_human_review`
   is a Pydantic validator that sets this field to `True` no matter what
   JSON the model produced - even if a future prompt regression, a
   different model, or an adversarial input caused the model to return
   `false`, the application-level guarantee holds.

3. **The API response includes a second, independent copy of the same
   guarantee** at the top level (`human_review_required` in the
   `POST /api/diagnose` response), plus a `safety_notice` string, so
   the frontend never has to reach into the AI's own JSON to know
   whether review is required - it's structurally always required.

4. **There is no code path that writes a diagnosis anywhere without a
   human decision attached.** The only mutation the application ever
   performs is `POST /api/reviews`, and every review row requires an
   explicit `human_decision` of `ACCEPTED`, `EDITED`, or `REJECTED` (see
   `backend/ai/schemas.py::ReviewCreateRequest` and
   `backend/services/review_service.py::create_review`). There is no
   "auto-accept" endpoint, no background job, and no code path that
   applies fix_steps to a device.

5. **A REJECTED decision requires a non-empty reason.**
   `ReviewCreateRequest._require_reason_if_rejected` is a Pydantic
   model-level validator (not a field-level one - Pydantic v2 skips
   field validators on values left at their default, which would have
   let an empty reason slip through; see the comment in `schemas.py` for
   why this matters). This is enforced at the API layer, not just in
   the frontend UI, so it can't be bypassed by calling the API directly.

6. **Malformed AI output never crashes the app and never gets treated
   as a valid diagnosis.** `backend/ai/diagnosis.py::parse_ai_response`
   is wrapped in a try/except inside `diagnose()`; any JSON parse
   failure or Pydantic validation failure results in a clean `error`
   field, not an exception propagating to the user, and critically,
   `ai_diagnosis` is `None` in that case - there is nothing for a human
   to accidentally rubber-stamp.

## Evidence discipline

The AI is instructed (and, in mock mode, mechanically constructed) to:

- Base every claim only on the symptom, topology note, and show-command
  output actually provided - never invent interfaces, IPs, VLANs,
  routes, or ACL entries.
- Distinguish observed facts (`evidence`) from inference
  (`reasoning_summary`).
- Calibrate `confidence` / `confidence_label` rather than presenting
  uncertain diagnoses as fact.
- Recommend a `next_command` when evidence is insufficient, instead of
  guessing.

The dataset's `expected_fault`, `expected_evidence`, `expected_fix`,
`expected_next_command`, and `verification_command` fields are ground
truth used only for offline dataset/test validation (see
`tests/test_checker.py::test_build_evidence_text_excludes_ground_truth_fields`)
- they are never sent to the AI. The AI reaches its own conclusion from
raw evidence, the same as a human troubleshooting the case would.

## Why 5+ corrected cases are in the dataset by default

`data/reviews.csv` ships pre-populated with 12 example reviews: 5
accepted, 3 edited, and 4 rejected. This isn't cosmetic - it's meant to
demonstrate, on day one, why human review matters even when the AI
sounds confident:

- **`REV-0009` / `ACL-002`** - the AI blamed a routing problem; the real
  cause was an ACL denying port 80, sitting in plain sight in the
  supplied `show access-lists` output. The AI didn't sufficiently use
  evidence it was already given.
- **`REV-0010` / `DNS-001`** - the AI blamed routing again; a successful
  raw-IP ping (evidence the AI had) should have ruled that out. The
  actual cause was a DHCP pool advertising the wrong DNS server.
- **`REV-0011` / `STP-001`** - the most important example: the AI
  recommended *disabling spanning-tree* on a healthy, correctly-blocking
  redundant link, which would have introduced a bridging loop risk. The
  human reviewer rejected a recommendation that would have made the
  network *less* safe, not just factually wrong. This is the clearest
  illustration in the dataset of why "AI suggests, human decides" is a
  safety property, not a formality.
- **`REV-0012` / `DUPIP-001`** - the AI defaulted to a generic "probably
  a bad cable" explanation instead of reading the supplied ARP table,
  which directly showed a duplicate-IP conflict.
- **`REV-0006` / `NAT-002`, `REV-0007` / `MASK-001`, `REV-0008` /
  `WIFI-002`** - edited cases where the AI's general direction was
  right but needed a human to sharpen it into something actually
  actionable, or to correctly reframe an intentional security control
  as a policy question rather than a bug.

Run `python3 checker.py --case STP-001` from `backend/rules/` yourself
and compare its (empty) output - a healthy blocking port isn't a
deterministic rule violation - against what `mock_data.py`'s scripted
AI response says for that case, to see the gap human review is meant to
catch.

## What NetSage AI deliberately does not do

- It does not execute any Cisco CLI command against any device.
- It does not have a "one-click apply fix" button anywhere in the UI.
- It does not average, merge, or otherwise combine the rule checker's
  findings with the AI's diagnosis into a single number or verdict -
  they are shown side by side so a human can weigh them.
- It does not hide or soften a REJECTED verdict in the dashboard's
  agreement-rate statistic; corrections are counted and surfaced, not
  smoothed over.
