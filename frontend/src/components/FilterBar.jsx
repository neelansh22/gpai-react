import { useState } from "react";
import { ChevronDown, X } from "lucide-react";
import { usePricingState } from "../state/PricingState";

function FilterDropdown({ label, filterKey, options }) {
  const { filters, toggleFilter } = usePricingState();
  const [open, setOpen] = useState(false);
  const selected = filters[filterKey] || [];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors ${
          selected.length > 0
            ? "border-sky-500/40 bg-sky-500/10 text-sky-200"
            : "border-slate-800 bg-slate-900/60 text-slate-300 hover:bg-slate-800"
        }`}
      >
        {label}
        {selected.length > 0 && (
          <span className="rounded-full bg-sky-500/30 px-1.5 text-xs">{selected.length}</span>
        )}
        <ChevronDown className="h-3.5 w-3.5" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute z-20 mt-2 max-h-64 w-56 overflow-y-auto rounded-xl border border-slate-800 bg-slate-900 p-2 shadow-xl">
            {options.length === 0 && <p className="px-2 py-1 text-xs text-slate-500">No options</p>}
            {options.map((opt) => (
              <label
                key={opt}
                className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(opt)}
                  onChange={() => toggleFilter(filterKey, opt)}
                  className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-sky-500 focus:ring-sky-500"
                />
                {opt}
              </label>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function FilterBar() {
  const { filterOptions, loadingOptions, clearFilters, activeFilterCount } = usePricingState();

  if (loadingOptions) {
    return <div className="mb-6 h-11 animate-pulse rounded-xl bg-slate-900/60" />;
  }

  return (
    <div className="mb-6 flex flex-wrap items-center gap-2">
      <FilterDropdown label="Part Class" filterKey="part_class" options={filterOptions.part_classes} />
      <FilterDropdown label="Condition" filterKey="condition" options={filterOptions.conditions} />
      <FilterDropdown label="Year" filterKey="year" options={filterOptions.years.map(String)} />
      {activeFilterCount > 0 && (
        <button
          onClick={clearFilters}
          className="flex items-center gap-1 rounded-xl px-3 py-2 text-sm font-medium text-rose-300 hover:bg-rose-500/10"
        >
          <X className="h-3.5 w-3.5" />
          Clear all
        </button>
      )}
    </div>
  );
}
