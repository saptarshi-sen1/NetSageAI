import { Check } from "lucide-react";

export type PipelineStage = "symptom" | "evidence" | "ai" | "review" | "verify";

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: "symptom", label: "Symptom" },
  { key: "evidence", label: "Evidence" },
  { key: "ai", label: "AI Hypothesis" },
  { key: "review", label: "Human Review" },
  { key: "verify", label: "Verification" },
];

export default function PipelineRail({ current }: { current: PipelineStage }) {
  const currentIndex = STAGES.findIndex((s) => s.key === current);

  return (
    <ol className="flex items-center gap-1 sm:gap-2">
      {STAGES.map((stage, i) => {
        const done = i < currentIndex;
        const active = i === currentIndex;
        return (
          <li key={stage.key} className="flex flex-1 items-center gap-1 sm:gap-2">
            <div className="flex flex-col items-center gap-1">
              <div
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold transition-colors ${
                  done
                    ? "border-signal-pass bg-signal-pass text-[#06231A]"
                    : active
                    ? "border-signal-info bg-signal-infoDim text-signal-info shadow-[0_0_0_3px_rgba(79,184,232,0.15)]"
                    : "border-surface-border bg-surface-2 text-ink-muted"
                }`}
              >
                {done ? <Check size={12} /> : i + 1}
              </div>
              <span
                className={`hidden text-center text-[10px] font-medium sm:block ${
                  active ? "text-ink-primary" : "text-ink-muted"
                }`}
              >
                {stage.label}
              </span>
            </div>
            {i < STAGES.length - 1 && (
              <div
                className={`h-px flex-1 ${done ? "bg-signal-pass" : "bg-surface-border"}`}
                aria-hidden="true"
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
