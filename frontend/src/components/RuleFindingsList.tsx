import { CheckCircle2 } from "lucide-react";
import type { Finding } from "../services/types";
import { SeverityBadge, StatusBadge } from "./Badges";

export default function RuleFindingsList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-surface-border bg-surface-1 px-3 py-2.5 text-sm text-ink-muted">
        <CheckCircle2 size={15} className="text-ink-muted" />
        No deterministic findings for this case. This doesn't mean the network is healthy - it
        means none of the rule checker's pattern matches fired on the supplied evidence.
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {findings.map((f, i) => (
        <li
          key={`${f.rule}-${i}`}
          className="rounded-md border border-surface-border bg-surface-1 px-3 py-2.5"
        >
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={f.status} />
            <SeverityBadge severity={f.severity} />
            <span className="font-mono text-[12px] text-ink-secondary">{f.rule}</span>
          </div>
          <p className="mt-1.5 text-sm text-ink-primary">{f.message}</p>
          {f.evidence && (
            <p className="mt-1 font-mono text-[12px] leading-relaxed text-ink-muted">
              {f.evidence}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
