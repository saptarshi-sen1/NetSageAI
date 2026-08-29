import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Archive, ArchiveRestore, Pencil, Plus, Search, SlidersHorizontal } from "lucide-react";
import { api, ApiError } from "../services/api";
import type { Case, CaseFacets } from "../services/types";
import { ArchivedBadge, CaseSeverityBadge, CaseSourceBadge } from "../components/Badges";
import CaseFormModal from "../components/CaseFormModal";

const ANY = "Any";

export default function CaseList() {
  const [cases, setCases] = useState<Case[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [conceptFilter, setConceptFilter] = useState(ANY);
  const [severityFilter, setSeverityFilter] = useState(ANY);
  const [osiFilter, setOsiFilter] = useState(ANY);
  const [difficultyFilter, setDifficultyFilter] = useState(ANY);
  const [showArchived, setShowArchived] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [facets, setFacets] = useState<CaseFacets | null>(null);

  const [formMode, setFormMode] = useState<null | "create" | Case>(null);
  const [facetsRefreshKey, setFacetsRefreshKey] = useState(0);
  const [statusUpdating, setStatusUpdating] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadCases = useCallback(() => {
    api
      .listCases({
        concept: conceptFilter === ANY ? undefined : conceptFilter,
        severity: severityFilter === ANY ? undefined : severityFilter,
        osi_layer: osiFilter === ANY ? undefined : osiFilter,
        difficulty: difficultyFilter === ANY ? undefined : difficultyFilter,
        search: query.trim() || undefined,
        include_archived: showArchived,
      })
      .then(setCases)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load cases"));
  }, [conceptFilter, severityFilter, osiFilter, difficultyFilter, query, showArchived]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  useEffect(() => {
    api.getCaseFacets().then(setFacets).catch(() => {
      // Non-fatal - filter dropdowns just fall back to "no options" if this fails.
    });
  }, [facetsRefreshKey]);

  const hasActiveFilters =
    conceptFilter !== ANY ||
    severityFilter !== ANY ||
    osiFilter !== ANY ||
    difficultyFilter !== ANY ||
    showArchived;

  function clearFilters() {
    setConceptFilter(ANY);
    setSeverityFilter(ANY);
    setOsiFilter(ANY);
    setDifficultyFilter(ANY);
    setShowArchived(false);
  }

  async function handleToggleArchive(c: Case, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setActionError(null);
    setStatusUpdating(c.case_id);
    try {
      await api.setCaseStatus(c.case_id, c.status === "archived" ? "active" : "archived");
      loadCases();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to update case status");
    } finally {
      setStatusUpdating(null);
    }
  }

  function handleEditClick(c: Case, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setFormMode(c);
  }

  const sortedByDifficulty = useMemo(() => {
    const order = { Easy: 0, Medium: 1, Hard: 2 };
    return cases ? [...cases].sort((a, b) => order[a.difficulty] - order[b.difficulty]) : [];
  }, [cases]);

  if (error) {
    return (
      <div className="rounded-lg border border-signal-fail/30 bg-signal-failDim/40 px-4 py-3 text-sm text-signal-fail">
        Couldn't load cases: {error}. Is the backend running on :8000?
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink-primary">Case Library</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            {cases ? `${cases.length} case${cases.length === 1 ? "" : "s"}` : "Loading…"} · select
            one to run the deterministic checker and request an AI diagnosis.
          </p>
        </div>
        <button
          onClick={() => setFormMode("create")}
          className="flex items-center gap-1.5 rounded-md bg-signal-pass px-3.5 py-2 text-sm font-semibold text-[#06231A] transition-opacity hover:opacity-90"
        >
          <Plus size={15} /> Create New Case
        </button>
      </div>

      {actionError && (
        <div className="rounded-md border border-signal-fail/30 bg-signal-failDim/40 px-3 py-2.5 text-sm text-signal-fail">
          {actionError}
        </div>
      )}

      <div className="space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by ID, title, or symptom…"
              className="w-full rounded-md border border-surface-border bg-surface-1 py-2 pl-9 pr-3 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-info focus:outline-none"
            />
          </div>
          <button
            onClick={() => setShowFilters((s) => !s)}
            className={`flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
              showFilters || hasActiveFilters
                ? "border-signal-info/40 bg-signal-infoDim/40 text-signal-info"
                : "border-surface-border bg-surface-1 text-ink-secondary hover:bg-surface-2"
            }`}
          >
            <SlidersHorizontal size={14} />
            Filters
            {hasActiveFilters && (
              <span className="ml-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-signal-info text-[10px] font-bold text-[#0A2733]">
                •
              </span>
            )}
          </button>
        </div>

        {showFilters && (
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-surface-border bg-surface-1 px-3 py-3">
            <FilterSelect
              label="Concept"
              value={conceptFilter}
              options={facets?.concepts ?? []}
              onChange={setConceptFilter}
            />
            <FilterSelect
              label="Severity"
              value={severityFilter}
              options={facets?.severities ?? []}
              onChange={setSeverityFilter}
            />
            <FilterSelect
              label="OSI layer"
              value={osiFilter}
              options={facets?.osi_layers ?? []}
              onChange={setOsiFilter}
            />
            <FilterSelect
              label="Difficulty"
              value={difficultyFilter}
              options={facets?.difficulties ?? []}
              onChange={setDifficultyFilter}
            />
            <label className="ml-auto flex items-center gap-1.5 text-xs text-ink-secondary">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => setShowArchived(e.target.checked)}
                className="rounded border-surface-border accent-signal-info"
              />
              Show archived
            </label>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="text-xs font-medium text-signal-info hover:underline"
              >
                Clear all
              </button>
            )}
          </div>
        )}
      </div>

      {!cases ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-lg border border-surface-border bg-surface-1" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sortedByDifficulty.map((c) => (
            <Link
              key={c.case_id}
              to={`/cases/${c.case_id}`}
              className={`group relative flex flex-col rounded-lg border p-4 shadow-panel transition-colors ${
                c.status === "archived"
                  ? "border-surface-border/60 bg-surface-1/50 opacity-70 hover:opacity-100"
                  : "border-surface-border bg-surface-1 hover:border-signal-info/40 hover:bg-surface-2/60"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] font-semibold text-signal-info">
                  {c.case_id}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => handleEditClick(c, e)}
                    className="rounded p-1 text-ink-muted opacity-0 pointer-events-none transition-opacity hover:bg-surface-3 hover:text-ink-primary group-hover:opacity-100 group-hover:pointer-events-auto"
                    title="Edit case"
                    aria-label={`Edit ${c.case_id}`}
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    onClick={(e) => handleToggleArchive(c, e)}
                    disabled={statusUpdating === c.case_id}
                    className="rounded p-1 text-ink-muted opacity-0 pointer-events-none transition-opacity hover:bg-surface-3 hover:text-ink-primary group-hover:opacity-100 group-hover:pointer-events-auto disabled:opacity-50"
                    title={c.status === "archived" ? "Restore case" : "Archive case"}
                    aria-label={c.status === "archived" ? `Restore ${c.case_id}` : `Archive ${c.case_id}`}
                  >
                    {c.status === "archived" ? <ArchiveRestore size={13} /> : <Archive size={13} />}
                  </button>
                </div>
              </div>
              <h3 className="mt-2 text-sm font-semibold text-ink-primary group-hover:text-white">
                {c.title}
              </h3>
              <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-ink-secondary">
                {c.symptom}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[11px] text-ink-muted">
                <span className="rounded border border-surface-border px-1.5 py-0.5">
                  {c.osi_layer}
                </span>
                <span className="rounded border border-surface-border px-1.5 py-0.5">
                  {c.concept}
                </span>
                <CaseSeverityBadge severity={c.severity} />
                {c.status === "archived" && <ArchivedBadge />}
                <span className="ml-auto flex items-center gap-1.5">
                  <CaseSourceBadge source={c.source} />
                  {c.difficulty}
                </span>
              </div>
            </Link>
          ))}
          {sortedByDifficulty.length === 0 && (
            <p className="col-span-full py-8 text-center text-sm text-ink-muted">
              No cases match your filters.
            </p>
          )}
        </div>
      )}

      {formMode && (
        <CaseFormModal
          existingCase={formMode === "create" ? undefined : formMode}
          onClose={() => setFormMode(null)}
          onSaved={() => {
            setFormMode(null);
            loadCases();
            setFacetsRefreshKey((k) => k + 1);
          }}
        />
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-1.5 text-xs text-ink-secondary">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-surface-border bg-surface-2 px-2 py-1.5 text-xs text-ink-primary focus:border-signal-info focus:outline-none"
      >
        <option value={ANY}>{ANY}</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
