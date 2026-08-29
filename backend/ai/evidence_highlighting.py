"""
Evidence highlighting for the AI Diagnosis UI.

The AI's `evidence` field (see backend/ai/schemas.py::AIDiagnosis) is a
list of short, human-written sentences describing what in the supplied
show-command output supports the diagnosis - e.g. "show interfaces
fa0/6 switchport shows Fa0/6 access VLAN is 20, not 10." These
sentences are PARAPHRASED summaries, not verbatim quotes of the raw
output, so there is no exact substring relationship between an
evidence sentence and the show_outputs text in general.

What this module does instead: extract identifiable technical tokens
from each evidence sentence (interface names like "Fa0/6", VLAN
references like "VLAN 10", IP/CIDR addresses, standalone show-command
names) and find every place those SPECIFIC tokens literally appear in
the raw show_outputs text. This gives a genuinely useful "here's roughly
where in the output this evidence point is grounded" highlight for the
tokens that do line up - while making no claim about matching the full
sentence, and leaving evidence sentences with no locatable tokens
un-highlighted rather than guessing.

This is intentionally NOT a claim that the highlighted spans are the
ONLY text supporting the evidence, or that missing highlights mean the
evidence is unsupported - it is a best-effort readability aid. See
docs/responsible_ai.md for why the AI's evidence claims themselves are
already constrained (prompt-level "never claim evidence that does not
exist") separately from this highlighting layer.
"""
from __future__ import annotations

import re
from typing import List

from pydantic import BaseModel

# Ordered so longer/more specific patterns are tried before shorter
# generic ones; findall() below dedupes and preserves the union of all
# matches per evidence sentence regardless of order.
_TOKEN_PATTERNS = [
    # CIDR networks, e.g. 172.16.5.0/24
    r"\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b",
    # Bare IPv4 addresses, e.g. 10.10.20.1
    r"\b\d{1,3}(?:\.\d{1,3}){3}\b",
    # Interface names, e.g. Fa0/6, GigabitEthernet0/1.10, Serial0/0/0
    r"\b(?:Gi(?:gabitEthernet)?|Fa(?:stEthernet)?|Se(?:rial)?|Te(?:nGigabitEthernet)?|Vlan|Loopback|Po(?:rt-channel)?|Dot11Radio)\d+(?:/\d+)*(?:\.\d+)?\b",
    # VLAN references, e.g. "VLAN 10", "vlan40"
    r"\bVLAN\s?\d{1,4}\b",
    # MAC addresses, e.g. 00E0.1234.ABCD
    r"\b[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\b",
]
_TOKEN_RE = re.compile("|".join(_TOKEN_PATTERNS), re.IGNORECASE)

# Minimum token length to bother highlighting - avoids highlighting
# every stray "10" or "1" that would make the output more noisy, not
# more readable.
_MIN_TOKEN_LENGTH = 4


class EvidenceSpan(BaseModel):
    start: int
    end: int
    text: str


class EvidenceHighlight(BaseModel):
    evidence_text: str
    spans: List[EvidenceSpan]


def extract_tokens(evidence_sentence: str) -> List[str]:
    """Pull out the identifiable technical tokens from one evidence
    sentence. Deduplicated, order-preserving."""
    seen = set()
    tokens = []
    for match in _TOKEN_RE.finditer(evidence_sentence):
        token = match.group(0).strip()
        if len(token) < _MIN_TOKEN_LENGTH:
            continue
        key = token.lower()
        if key not in seen:
            seen.add(key)
            tokens.append(token)
    return tokens


def find_spans_for_token(show_outputs: str, token: str) -> List[EvidenceSpan]:
    """Every literal (case-insensitive) occurrence of `token` in
    show_outputs, as character-offset spans into that exact string -
    the frontend renders show_outputs verbatim, so these offsets are
    valid directly against it with no re-processing needed client-side."""
    spans = []
    pattern = re.compile(re.escape(token), re.IGNORECASE)
    for match in pattern.finditer(show_outputs):
        spans.append(EvidenceSpan(start=match.start(), end=match.end(), text=match.group(0)))
    return spans


def highlight_evidence(show_outputs: str, evidence: List[str]) -> List[EvidenceHighlight]:
    """Build one EvidenceHighlight per evidence sentence. A sentence
    with no locatable tokens gets an empty spans list - the frontend
    should render it as plain (unhighlighted) evidence text rather than
    treating that as an error."""
    results = []
    for sentence in evidence:
        tokens = extract_tokens(sentence)
        spans: List[EvidenceSpan] = []
        seen_ranges = set()
        for token in tokens:
            for span in find_spans_for_token(show_outputs, token):
                range_key = (span.start, span.end)
                if range_key not in seen_ranges:
                    seen_ranges.add(range_key)
                    spans.append(span)
        spans.sort(key=lambda s: s.start)
        results.append(EvidenceHighlight(evidence_text=sentence, spans=spans))
    return results
