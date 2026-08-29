import { ShieldAlert } from "lucide-react";

export default function SafetyBanner({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={`flex items-start gap-3 rounded-lg border border-signal-warn/30 bg-signal-warnDim/60 text-ink-primary ${
        compact ? "px-3 py-2" : "px-4 py-3"
      }`}
      role="note"
      aria-label="Responsible AI notice"
    >
      <ShieldAlert
        className="mt-0.5 shrink-0 text-signal-warn"
        size={compact ? 16 : 18}
        aria-hidden="true"
      />
      <p className={compact ? "text-xs leading-snug" : "text-sm leading-snug"}>
        <span className="font-semibold text-signal-warn">AI recommendations are advisory.</span>{" "}
        A human reviewer must approve every diagnosis before a fix is accepted. NetSage AI never
        applies configuration changes automatically.
      </p>
    </div>
  );
}
