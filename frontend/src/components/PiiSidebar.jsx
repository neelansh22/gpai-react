import { NavLink } from "react-router-dom";
import { ShieldCheck, ArrowLeft, ScanSearch } from "lucide-react";

const NAV_ITEMS = [
  { to: "/pii", label: "Overview", icon: ShieldCheck, end: true },
  { to: "/pii/playground", label: "Detect & Redact", icon: ScanSearch, end: false },
];

export default function PiiSidebar() {
  return (
    <aside className="flex h-full w-72 shrink-0 flex-col overflow-y-auto border-r border-slate-800/70 bg-slate-950/80 px-4 py-6">
      <div className="mb-4 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-rose-500 to-orange-400 shadow-glow">
          <ShieldCheck className="h-6 w-6 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold leading-tight text-white">int-pii</p>
          <p className="text-xs text-slate-400">PII Detection & Redaction</p>
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
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                isActive
                  ? "bg-gradient-to-r from-rose-500/20 to-orange-500/10 text-white ring-1 ring-rose-500/30"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-6 rounded-2xl border border-slate-800/70 bg-slate-900/50 p-3">
        <p className="text-[11px] leading-relaxed text-slate-500">
          Runs a regex + GLiNER (ONNX) hybrid pipeline locally on the backend — no third-party API calls, no
          data retention. Uploaded files stay in memory and expire after 30 minutes.
        </p>
      </div>
    </aside>
  );
}
