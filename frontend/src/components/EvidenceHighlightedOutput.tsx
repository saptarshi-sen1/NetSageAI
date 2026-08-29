import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, SearchX, Terminal } from "lucide-react";
import type { EvidenceHighlight } from "../services/types";

interface Props {
  showOutputs: string;
  evidenceHighlights: EvidenceHighlight[];
  /** Fallback plain evidence strings, used only if evidenceHighlights
   * is null/empty (e.g. an older cached response) - so the evidence
   * list still renders something even without highlight data. */
  fallbackEvidence?: string[];
  defaultOpen?: boolean;
}

/**
 * IMPORTANT: every highlighted span rendered here comes directly from
 * the backend's deterministic token match (backend/ai/evidence_highlighting.py)
 * - exact character offsets into the SAME show_outputs string rendered
 * below. Nothing here infers, guesses, or fuzzy-matches on the frontend;
 * if the backend found no locatable token for an evidence sentence, that
 * sentence is rendered with an explicit "no exact matching span found"
 * notice rather than a fabricated highlight.
 */
export default function EvidenceHighlightedOutput({
  showOutputs,
  evidenceHighlights,
  fallbackEvidence,
  defaultOpen = false,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [activeIndex, setActiveIndex] = useState<number | null>(
    evidenceHighlights.length > 0 ? 0 : null
  );

  const items: EvidenceHighlight[] =
    evidenceHighlights.length > 0
      ? evidenceHighlights
      : (fallbackEvidence ?? []).map((text) => ({ evidence_text: text, spans: [] }));

  const activeItem = activeIndex !== null ? items[activeIndex] : null;
  const activeSpans = activeItem?.spans ?? [];

  // Build the rendered output as a sequence of plain-text and
  // highlighted-text segments, split at the active item's span
  // boundaries. Spans are already sorted and de-duplicated by the
  // backend, but we defensively sort here too since this rendering
  // logic depends on non-overlapping, ascending order to be correct.
  const segments = useMemo(() => {
    if (activeSpans.length === 0) {
      return [{ text: showOutputs, highlighted: false }];
    }
    const sorted = [...activeSpans].sort((a, b) => a.start - b.start);
    const parts: { text: string; highlighted: boolean }[] = [];
    let cursor = 0;
    for (const span of sorted) {
      if (span.start < cursor) continue; // guard against any overlap
      if (span.start > cursor) {
        parts.push({ text: showOutputs.slice(cursor, span.start), highlighted: false });
      }
      parts.push({ text: showOutputs.slice(span.start, span.end), highlighted: true });
      cursor = span.end;
    }
    if (cursor < showOutputs.length) {
      parts.push({ text: showOutputs.slice(cursor), highlighted: false });
    }
    return parts;
  }, [showOutputs, activeSpans]);

  return (
    <div className="overflow-hidden rounded-lg border border-surface-border bg-[#0A0E13]">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium text-ink-secondary transition-colors hover:bg-surface-2/50"
      >
        <span className="flex items-center gap-2">
          <Terminal size={14} className="text-signal-info" />
          show-command output
          {items.length > 0 && (
            <span className="text-[11px] font-normal text-ink-muted">
              - select an evidence item below to highlight where it's grounded
            </span>
          )}
        </span>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>

      {open && (
        <div className="border-t border-surface-border">
          {items.length > 0 && (
            <div className="space-y-1.5 border-b border-surface-border px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                Observed evidence
              </p>
              <ul className="space-y-1">
                {items.map((item, i) => {
                  const isActive = i === activeIndex;
                  const hasMatch = item.spans.length > 0;
                  return (
                    <li key={i}>
                      <button
                        type="button"
                        onClick={() => setActiveIndex(i)}
                        onMouseEnter={() => setActiveIndex(i)}
                        className={`flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                          isActive
                            ? "bg-signal-infoDim/40 text-ink-primary"
                            : "text-ink-secondary hover:bg-surface-2/60"
                        }`}
                      >
                        <span
                          className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${
                            hasMatch ? "bg-signal-info" : "bg-ink-muted"
                          }`}
                        />
                        <span className="flex-1 font-mono text-[12.5px] leading-relaxed">
                          {item.evidence_text}
                        </span>
                        {!hasMatch && (
                          <span className="flex shrink-0 items-center gap-1 whitespace-nowrap text-[10px] text-ink-muted">
                            <SearchX size={11} /> no exact match
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
              {activeItem && !activeItem.spans.length && (
                <p className="rounded border border-surface-border bg-surface-2/40 px-2 py-1.5 text-[11px] leading-relaxed text-ink-muted">
                  No exact matching span found in the supplied output for this evidence item.
                  The AI's evidence text is a summary - it may still be accurate even without a
                  literal text match below.
                </p>
              )}
            </div>
          )}
          <div className="px-4 py-3">
            <pre className="mono-block text-ink-secondary">
              {segments.map((seg, i) =>
                seg.highlighted ? (
                  <mark
                    key={i}
                    className="rounded-sm bg-signal-warn/30 px-0.5 text-signal-warn ring-1 ring-signal-warn/50"
                  >
                    {seg.text}
                  </mark>
                ) : (
                  <span key={i}>{seg.text}</span>
                )
              )}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
