import { useState } from "react";
import { Loader2, X } from "lucide-react";
import { api, ApiError } from "../services/api";
import type { Case, CaseFormFields } from "../services/types";

const OSI_LAYERS = ["Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 7"];
const SEVERITIES: CaseFormFields["severity"][] = ["Low", "Medium", "High", "Critical"];
const DIFFICULTIES: CaseFormFields["difficulty"][] = ["Easy", "Medium", "Hard"];

const EMPTY_FORM: CaseFormFields = {
  title: "",
  symptom: "",
  topology_note: "",
  show_outputs: "",
  expected_fault: "",
  osi_layer: "Layer 3",
  concept: "",
  severity: "Medium",
  expected_evidence: "",
  expected_next_command: "",
  expected_fix: "",
  verification_command: "",
  difficulty: "Medium",
};

const REQUIRED_FIELDS: (keyof CaseFormFields)[] = [
  "title",
  "symptom",
  "topology_note",
  "show_outputs",
  "expected_fault",
  "osi_layer",
  "concept",
];

interface Props {
  /** When editing, pass the existing case; when creating, omit it. */
  existingCase?: Case;
  onClose: () => void;
  onSaved: (savedCase: Case) => void;
}

type FieldConfig = {
  key: keyof CaseFormFields;
  label: string;
  hint?: string;
  multiline?: boolean;
  monospace?: boolean;
  rows?: number;
};

const TEXT_FIELDS: FieldConfig[] = [
  { key: "title", label: "Title" },
  {
    key: "symptom",
    label: "Symptom",
    hint: "What the user/learner observes - written in plain language.",
    multiline: true,
    rows: 3,
  },
  {
    key: "topology_note",
    label: "Topology note",
    hint: "Devices and connections relevant to the fault.",
    multiline: true,
    rows: 3,
  },
  {
    key: "show_outputs",
    label: "Show-command outputs",
    hint: "Paste real Cisco show-command output. Only include what's actually needed to diagnose the fault.",
    multiline: true,
    monospace: true,
    rows: 10,
  },
  {
    key: "expected_fault",
    label: "Expected fault",
    hint: "The correct diagnosis - used as ground truth, never shown to a student before they answer in Practice Mode.",
    multiline: true,
    rows: 3,
  },
  {
    key: "expected_evidence",
    label: "Expected evidence",
    hint: "Which parts of the show output actually support the diagnosis.",
    multiline: true,
    rows: 2,
  },
  { key: "expected_next_command", label: "Expected next command", monospace: true },
  {
    key: "expected_fix",
    label: "Expected fix",
    multiline: true,
    rows: 2,
  },
  { key: "verification_command", label: "Verification command", monospace: true },
];

export default function CaseFormModal({ existingCase, onClose, onSaved }: Props) {
  const isEditing = Boolean(existingCase);
  const [form, setForm] = useState<CaseFormFields>(() =>
    existingCase
      ? {
          title: existingCase.title,
          symptom: existingCase.symptom,
          topology_note: existingCase.topology_note,
          show_outputs: existingCase.show_outputs,
          expected_fault: existingCase.expected_fault,
          osi_layer: existingCase.osi_layer,
          concept: existingCase.concept,
          severity: existingCase.severity,
          expected_evidence: existingCase.expected_evidence,
          expected_next_command: existingCase.expected_next_command,
          expected_fix: existingCase.expected_fix,
          verification_command: existingCase.verification_command,
          difficulty: existingCase.difficulty,
        }
      : EMPTY_FORM
  );
  const [createdBy, setCreatedBy] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState<Set<string>>(new Set());

  function setField<K extends keyof CaseFormFields>(key: K, value: CaseFormFields[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function markTouched(key: string) {
    setTouched((t) => new Set(t).add(key));
  }

  const missingRequired = REQUIRED_FIELDS.filter((key) => !form[key]?.trim());
  const isValid = missingRequired.length === 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(new Set(REQUIRED_FIELDS));
    if (!isValid) return;

    setSaving(true);
    setError(null);
    try {
      const saved = isEditing
        ? await api.updateCase(existingCase!.case_id, form)
        : await api.createCase({ ...form, created_by: createdBy || "Anonymous" });
      onSaved(saved);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to save case");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 px-4 py-8 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-2xl rounded-lg border border-surface-border bg-surface-1 shadow-panel">
        <div className="sticky top-0 z-10 flex items-center justify-between rounded-t-lg border-b border-surface-border bg-surface-1 px-5 py-3.5">
          <div>
            <h2 className="text-base font-semibold text-ink-primary">
              {isEditing ? `Edit ${existingCase!.case_id}` : "Create New Case"}
            </h2>
            <p className="mt-0.5 text-xs text-ink-muted">
              {isEditing
                ? "Changes are saved immediately and apply to future diagnosis runs."
                : "New cases flow through the exact same Check → Diagnose → Review pipeline as the seed dataset."}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink-primary"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
          {error && (
            <div className="rounded-md border border-signal-fail/30 bg-signal-failDim/40 px-3 py-2.5 text-sm text-signal-fail">
              {error}
            </div>
          )}

          {/* Classification row */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <label className="block text-xs font-medium text-ink-secondary">
              OSI layer
              <select
                value={form.osi_layer}
                onChange={(e) => setField("osi_layer", e.target.value)}
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-2 px-2.5 py-1.5 text-sm text-ink-primary focus:border-signal-info focus:outline-none"
              >
                {OSI_LAYERS.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-medium text-ink-secondary">
              Concept
              <input
                value={form.concept}
                onChange={(e) => setField("concept", e.target.value)}
                onBlur={() => markTouched("concept")}
                placeholder="e.g. VLAN, NAT, DHCP"
                className={`mt-1 w-full rounded-md border bg-surface-2 px-2.5 py-1.5 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-info focus:outline-none ${
                  touched.has("concept") && !form.concept.trim()
                    ? "border-signal-fail/60"
                    : "border-surface-border"
                }`}
              />
            </label>
            <label className="block text-xs font-medium text-ink-secondary">
              Severity
              <select
                value={form.severity}
                onChange={(e) => setField("severity", e.target.value as CaseFormFields["severity"])}
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-2 px-2.5 py-1.5 text-sm text-ink-primary focus:border-signal-info focus:outline-none"
              >
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-medium text-ink-secondary">
              Difficulty
              <select
                value={form.difficulty}
                onChange={(e) => setField("difficulty", e.target.value as CaseFormFields["difficulty"])}
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-2 px-2.5 py-1.5 text-sm text-ink-primary focus:border-signal-info focus:outline-none"
              >
                {DIFFICULTIES.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {TEXT_FIELDS.map((field) => {
            const isRequired = REQUIRED_FIELDS.includes(field.key);
            const isEmpty = !form[field.key]?.trim();
            const showError = isRequired && touched.has(field.key) && isEmpty;
            const commonProps = {
              value: form[field.key],
              onChange: (e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) =>
                setField(field.key, e.target.value),
              onBlur: () => markTouched(field.key),
              className: `mt-1 w-full rounded-md border bg-surface-2 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-info focus:outline-none ${
                field.monospace ? "font-mono text-[12.5px]" : ""
              } ${showError ? "border-signal-fail/60" : "border-surface-border"}`,
            };
            return (
              <label key={field.key} className="block text-xs font-medium text-ink-secondary">
                <span className="flex items-center gap-1">
                  {field.label}
                  {isRequired && <span className="text-signal-fail">*</span>}
                </span>
                {field.hint && <span className="mt-0.5 block text-[11px] font-normal text-ink-muted">{field.hint}</span>}
                {field.multiline ? (
                  <textarea {...commonProps} rows={field.rows ?? 3} />
                ) : (
                  <input {...commonProps} />
                )}
                {showError && (
                  <span className="mt-1 block text-[11px] text-signal-fail">This field is required.</span>
                )}
              </label>
            );
          })}

          {!isEditing && (
            <label className="block text-xs font-medium text-ink-secondary">
              Your name (optional)
              <input
                value={createdBy}
                onChange={(e) => setCreatedBy(e.target.value)}
                placeholder="Anonymous"
                className="mt-1 w-full rounded-md border border-surface-border bg-surface-2 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-info focus:outline-none"
              />
            </label>
          )}

          <div className="flex items-center justify-between border-t border-surface-border pt-4">
            <p className="text-[11px] text-ink-muted">
              {missingRequired.length > 0
                ? `${missingRequired.length} required field${missingRequired.length > 1 ? "s" : ""} remaining`
                : "Ready to save"}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-surface-border px-3.5 py-2 text-sm text-ink-secondary transition-colors hover:bg-surface-2"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-1.5 rounded-md bg-signal-info px-4 py-2 text-sm font-semibold text-[#0A2733] transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {saving && <Loader2 size={14} className="animate-spin" />}
                {isEditing ? "Save changes" : "Create case"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
