"""
Tests for backend/ai/evidence_highlighting.py.

Covers: token extraction from evidence sentences, offset correctness
(the span text must exactly match show_outputs[start:end]), graceful
handling of unmatchable evidence, and a full-dataset sweep to catch any
case-specific crash or offset bug across all 30 seed cases.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ai.evidence_highlighting import (
    EvidenceHighlight,
    EvidenceSpan,
    extract_tokens,
    find_spans_for_token,
    highlight_evidence,
)


# --------------------------------------------------------------------------
# Token extraction
# --------------------------------------------------------------------------
def test_extract_interface_token():
    tokens = extract_tokens("show interfaces fa0/6 switchport shows Fa0/6 is down")
    assert "Fa0/6" in tokens or "fa0/6" in tokens


def test_extract_gigabit_interface_token():
    tokens = extract_tokens("GigabitEthernet0/1.10 has no IP address configured")
    assert any("GigabitEthernet0/1.10" == t for t in tokens)


def test_extract_vlan_token():
    tokens = extract_tokens("VLAN 10 exists and holds the file server's segment")
    assert any("VLAN 10" == t.strip() or t.strip().lower() == "vlan 10" for t in tokens)


def test_extract_ip_address_token():
    tokens = extract_tokens("the gateway 10.10.20.1 is reachable")
    assert "10.10.20.1" in tokens


def test_extract_cidr_token():
    tokens = extract_tokens("172.16.5.0/24 is absent from the routing table")
    assert "172.16.5.0/24" in tokens


def test_extract_mac_address_token():
    tokens = extract_tokens("00E0.1234.ABCD is mapped to two different ports")
    assert any(t.lower() == "00e0.1234.abcd" for t in tokens)


def test_extract_tokens_empty_for_generic_sentence():
    tokens = extract_tokens("this is a generic sentence with no technical identifiers")
    assert tokens == []


def test_extract_tokens_deduplicates():
    tokens = extract_tokens("Fa0/6 is down. Fa0/6 was previously up.")
    assert tokens.count("Fa0/6") <= 1  # case-insensitive dedup, exact casing preserved once


def test_short_tokens_filtered_out():
    """Tokens shorter than the minimum length shouldn't be extracted,
    to avoid highlighting noise like a bare '10'."""
    tokens = extract_tokens("port 10 was mentioned")
    assert "10" not in tokens


# --------------------------------------------------------------------------
# Span finding / offset correctness
# --------------------------------------------------------------------------
def test_find_spans_for_token_exact_match():
    show_outputs = "Interface Fa0/6 is up\nFa0/6 is in VLAN 20"
    spans = find_spans_for_token(show_outputs, "Fa0/6")
    assert len(spans) == 2
    for span in spans:
        assert show_outputs[span.start : span.end] == span.text


def test_find_spans_for_token_case_insensitive():
    show_outputs = "interface fa0/6 status: up"
    spans = find_spans_for_token(show_outputs, "Fa0/6")
    assert len(spans) == 1
    assert spans[0].text == "fa0/6"  # preserves original casing from the source text


def test_find_spans_for_token_no_match():
    spans = find_spans_for_token("no relevant content here", "Gi0/1")
    assert spans == []


def test_find_spans_offsets_are_byte_exact():
    show_outputs = "aaa Fa0/6 bbb Fa0/6 ccc"
    spans = find_spans_for_token(show_outputs, "Fa0/6")
    assert len(spans) == 2
    assert show_outputs[spans[0].start : spans[0].end] == "Fa0/6"
    assert show_outputs[spans[1].start : spans[1].end] == "Fa0/6"
    assert spans[0].start < spans[1].start


# --------------------------------------------------------------------------
# Full highlight_evidence() behavior
# --------------------------------------------------------------------------
def test_highlight_evidence_returns_one_result_per_sentence():
    show_outputs = "Fa0/6 is in VLAN 20"
    evidence = ["Fa0/6 is misconfigured", "this has no technical tokens at all"]
    results = highlight_evidence(show_outputs, evidence)
    assert len(results) == 2
    assert all(isinstance(r, EvidenceHighlight) for r in results)


def test_highlight_evidence_unmatchable_sentence_gets_empty_spans():
    """A sentence with no locatable tokens should degrade gracefully -
    empty spans list, not an error or a crash."""
    results = highlight_evidence("some show output", ["a purely conceptual conclusion"])
    assert results[0].spans == []
    assert results[0].evidence_text == "a purely conceptual conclusion"


def test_highlight_evidence_matched_sentence_has_valid_spans():
    show_outputs = "SW1# show vlan brief\nFa0/6 is in VLAN 20, not VLAN 10"
    results = highlight_evidence(show_outputs, ["Fa0/6 is in the wrong VLAN"])
    assert len(results[0].spans) >= 1
    for span in results[0].spans:
        assert show_outputs[span.start : span.end] == span.text


def test_highlight_evidence_empty_evidence_list():
    results = highlight_evidence("some output", [])
    assert results == []


def test_highlight_evidence_spans_are_sorted_by_position():
    show_outputs = "Gi0/1 up, then Fa0/6 down, then Gi0/1 mentioned again"
    results = highlight_evidence(show_outputs, ["Gi0/1 and Fa0/6 are both relevant"])
    spans = results[0].spans
    starts = [s.start for s in spans]
    assert starts == sorted(starts)


def test_highlight_evidence_no_duplicate_identical_spans():
    """If two extracted tokens both point at the same literal
    occurrence, it shouldn't be double-counted."""
    show_outputs = "Fa0/6 status up"
    results = highlight_evidence(show_outputs, ["Fa0/6 Fa0/6 Fa0/6"])  # same token repeated
    spans = results[0].spans
    ranges = [(s.start, s.end) for s in spans]
    assert len(ranges) == len(set(ranges))


# --------------------------------------------------------------------------
# (b) Partial token match - some tokens in a sentence resolve, others don't
# --------------------------------------------------------------------------
def test_highlight_evidence_partial_match_within_one_sentence():
    """A single evidence sentence can reference multiple tokens where
    only SOME are actually present in the show output. The ones that
    match should be highlighted; the sentence should still be returned
    with those (partial) spans rather than being treated as fully
    matched or fully unmatched."""
    show_outputs = "Fa0/6 is up\nVLAN 20 is active"
    # Gi0/1 does not appear anywhere in show_outputs - only Fa0/6 does.
    results = highlight_evidence(show_outputs, ["Fa0/6 and Gi0/1 are both relevant here"])
    spans = results[0].spans
    matched_texts = {s.text.lower() for s in spans}
    assert "fa0/6" in matched_texts
    assert not any("gi0/1" in t for t in matched_texts)
    # Confirm every span found is still byte-exact.
    for span in spans:
        assert show_outputs[span.start : span.end] == span.text


def test_highlight_evidence_partial_match_does_not_fabricate_missing_token():
    """The unmatched token (Gi0/1) must never appear as a highlighted
    span, even partially/fuzzily - a partial sentence match only
    highlights the SPECIFIC substrings that are genuinely present."""
    show_outputs = "Only Fa0/6 appears in this output, nothing else technical."
    results = highlight_evidence(show_outputs, ["Compare Fa0/6 against Gi0/2 and 10.10.10.99"])
    spans = results[0].spans
    for span in spans:
        assert span.text.lower() == "fa0/6"
    assert len(spans) == 1


# --------------------------------------------------------------------------
# (f) Malformed / empty show output
# --------------------------------------------------------------------------
def test_highlight_evidence_empty_show_outputs_string():
    """An empty show_outputs string must not crash - every evidence
    sentence should come back with empty spans (nothing to match
    against), not raise an exception."""
    results = highlight_evidence("", ["Fa0/6 is misconfigured", "VLAN 10 issue"])
    assert len(results) == 2
    assert all(r.spans == [] for r in results)


def test_highlight_evidence_whitespace_only_show_outputs():
    results = highlight_evidence("   \n\n\t  ", ["Fa0/6 is misconfigured"])
    assert results[0].spans == []


def test_highlight_evidence_show_outputs_with_null_like_content():
    """Show output containing unusual/control characters shouldn't
    crash the regex matching or offset computation."""
    malformed = "Fa0/6\x00\x01 status\r\n\r\n up \ufeff"
    results = highlight_evidence(malformed, ["Fa0/6 status"])
    # Should not raise; Fa0/6 is still present and should be found.
    assert any(s.text.lower() == "fa0/6" for s in results[0].spans)
    for span in results[0].spans:
        assert malformed[span.start : span.end] == span.text


def test_highlight_evidence_empty_evidence_sentence_in_list():
    """A blank string mixed into the evidence list shouldn't crash -
    it simply has no tokens and no spans."""
    results = highlight_evidence("Fa0/6 is up", ["", "Fa0/6 is relevant", "   "])
    assert len(results) == 3
    assert results[0].spans == []
    assert results[2].spans == []


def test_extract_tokens_handles_empty_string():
    assert extract_tokens("") == []


def test_find_spans_for_token_empty_show_outputs():
    assert find_spans_for_token("", "Fa0/6") == []


def test_highlight_evidence_very_long_show_outputs_does_not_crash():
    """Sanity check against a large, realistic-scale show output blob
    (many repeated lines) to catch any pathological performance or
    offset-tracking issue at scale."""
    large_output = "\n".join(f"Fa0/{i} status up, VLAN {i % 40}" for i in range(500))
    results = highlight_evidence(large_output, ["Fa0/6 was reassigned to VLAN 20"])
    for span in results[0].spans:
        assert large_output[span.start : span.end] == span.text


# --------------------------------------------------------------------------
# Full-dataset sweep: no crashes, no offset bugs, on real cases
# --------------------------------------------------------------------------
def test_highlight_evidence_works_across_full_dataset_with_mock_ai():
    """Runs highlighting against every seed case's real show_outputs
    paired with real (mock-mode) AI evidence, verifying no exceptions
    and every returned span is byte-exact against that case's
    show_outputs."""
    from backend.ai.client import MockAIClient
    from backend.ai.diagnosis import diagnose
    from backend.services.case_service import list_cases

    total_cases_checked = 0
    for case in list_cases():
        result = diagnose(case, ai_client=MockAIClient())
        if not result.ai_diagnosis or not result.ai_diagnosis.evidence:
            continue
        highlights = highlight_evidence(case["show_outputs"], result.ai_diagnosis.evidence)
        for h in highlights:
            for span in h.spans:
                assert case["show_outputs"][span.start : span.end] == span.text, (
                    f"{case['case_id']}: offset mismatch for span {span}"
                )
        total_cases_checked += 1

    assert total_cases_checked > 0, "No cases were actually checked - test is vacuous"
