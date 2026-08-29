import { useState } from "react";
import { ChevronDown, ChevronRight, Terminal } from "lucide-react";

export default function ShowOutputBlock({
  content,
  defaultOpen = false,
}: {
  content: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

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
        </span>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {open && (
        <div className="border-t border-surface-border px-4 py-3">
          <pre className="mono-block text-ink-secondary">{content}</pre>
        </div>
      )}
    </div>
  );
}
