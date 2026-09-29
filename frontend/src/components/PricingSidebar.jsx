import { NavLink } from "react-router-dom";
import { Gauge, ScatterChart, TrendingUp, Table2, ArrowLeft, PlaneTakeoff } from "lucide-react";
import { usePricingState } from "../state/PricingState";
import Tooltip from "./Tooltip";

const NAV_ITEMS = [
  { to: "/pricing", label: "Overview", icon: Gauge, tip: "Snapshot of pricing corridors and key metrics across the parts catalog." },
  { to: "/pricing/corridor", label: "Corridor Analysis", icon: ScatterChart, tip: "Compare price vs. cost corridors to spot outliers and pricing opportunities." },
  { to: "/pricing/trend", label: "Yearly Trend", icon: TrendingUp, tip: "See how pricing corridors evolve year over year for selected parts." },
  { to: "/pricing/table", label: "Summary Table", icon: Table2, tip: "Drill into a sortable, filterable table of every part and price point." },
];

export default function PricingSidebar() {
  const { activeFilterCount } = usePricingState();

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col overflow-y-auto border-r border-slate-800/70 bg-slate-950/80 px-4 py-6">
      <div className="mb-4 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-400 to-cyan-500 shadow-glow">
          <PlaneTakeoff className="h-6 w-6 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="truncate text-sm font-semibold leading-tight text-white">Aerfin Analysis</p>
            <Tooltip
              accent="sky"
              title="Dynamic Pricing Corridor"
              content="Analyze part pricing corridors against cost and demand to find optimal price bands and flag outliers, backed by a synthetic Aerfin-style dataset."
            />
          </div>
          <p className="text-xs text-slate-400">Dynamic Pricing Corridor</p>
        </div>
      </div>

      <NavLink
        to="/"
        className="mb-4 flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-slate-500 hover:bg-slate-900 hover:text-slate-300"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to App Selector
      </NavLink>

      <nav className="flex-1 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, tip }) => (
          <div key={to} className="group relative">
            <NavLink
              to={to}
              end={to === "/pricing"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 pr-8 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-gradient-to-r from-sky-500/20 to-cyan-500/10 text-white ring-1 ring-sky-500/30"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{label}</span>
            </NavLink>
            {tip && (
              <span className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-100">
                <Tooltip accent="sky" title={label} content={tip} />
              </span>
            )}
          </div>
        ))}
      </nav>

      <div className="mt-6 rounded-2xl border border-slate-800/70 bg-slate-900/50 p-3">
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Active Filters
        </p>
        <p className="text-sm text-slate-300">
          {activeFilterCount > 0 ? `${activeFilterCount} filter(s) applied` : "None — showing all parts"}
        </p>
      </div>

      <p className="mt-4 px-2 text-[10px] leading-relaxed text-slate-600">
        Synthetic dataset generated to match Aerfin's Power BI pricing corridor schema.
      </p>
    </aside>
  );
}
