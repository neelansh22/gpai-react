import { useState } from "react";
import { NavLink } from "react-router-dom";
import { Radar, Gauge, DatabaseZap, BarChart3, Globe2, ArrowLeft, KeyRound } from "lucide-react";
import Tooltip from "./Tooltip";
import { monitorKey } from "../api/monitorClient";
import { useMonitorState } from "../state/MonitorState";

const NAV_ITEMS = [
  { to: "/monitor", label: "Overview", icon: Gauge, tip: "Headline numbers for the voice agent backend: traffic, cache efficiency and latency." },
  { to: "/monitor/cache", label: "Cache", icon: DatabaseZap, tip: "Is the cache earning its keep? Hit rate, misses, and what is currently warm in Table Storage." },
  { to: "/monitor/usage", label: "API Usage", icon: BarChart3, tip: "Which tools the agent calls, how often, how fast, and how many fail." },
  { to: "/monitor/heatmap", label: "Airport Heatmap", icon: Globe2, tip: "Where demand is concentrated, by departure and destination airport." },
];

const RANGES = ["24h", "7d", "30d"];

export default function MonitorSidebar() {
  const { range, setRange, refresh } = useMonitorState();
  const [key, setKey] = useState(monitorKey.get());

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col overflow-y-auto border-r border-slate-800/70 bg-slate-950/80 px-4 py-6">
      <div className="mb-4 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-glow">
          <Radar className="h-6 w-6 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="truncate text-sm font-semibold leading-tight text-white">Skyline Monitor</p>
            <Tooltip
              accent="amber"
              title="Skyline Monitor"
              content="Live observability for the Skyline voice travel agent: cache behaviour, API usage and airport demand, built from Application Insights and the cache table."
            />
          </div>
          <p className="text-xs text-slate-400">Voice Agent Analytics</p>
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
              end={to === "/monitor"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 pr-8 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-gradient-to-r from-amber-500/20 to-orange-500/10 text-white ring-1 ring-amber-500/30"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{label}</span>
            </NavLink>
            <span className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-100">
              <Tooltip accent="amber" title={label} content={tip} />
            </span>
          </div>
        ))}
      </nav>

      <div className="mt-6 space-y-2 rounded-2xl border border-slate-800/70 bg-slate-900/50 p-3">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Time range</p>
        <div className="flex gap-1.5">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition ${
                range === r
                  ? "bg-amber-500/20 text-amber-200 ring-1 ring-amber-500/40"
                  : "bg-slate-800/70 text-slate-400 hover:text-slate-200"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
        <button
          onClick={refresh}
          className="w-full rounded-lg bg-slate-800 px-2 py-1.5 text-xs font-semibold text-slate-200 ring-1 ring-slate-700 hover:bg-slate-700"
        >
          Refresh
        </button>
      </div>

      <div className="mt-4 space-y-2 rounded-2xl border border-slate-800/70 bg-slate-900/50 p-3">
        <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <KeyRound className="h-3 w-3" /> Access key
        </p>
        <input
          type="password"
          value={key}
          placeholder="Only if one is required"
          onChange={(e) => {
            setKey(e.target.value);
            monitorKey.set(e.target.value);
          }}
          onBlur={refresh}
          className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-2 py-1.5 text-xs text-slate-200 focus:border-amber-500 focus:outline-none"
        />
      </div>
    </aside>
  );
}
