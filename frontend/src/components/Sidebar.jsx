import { NavLink } from "react-router-dom";
import {
  Activity,
  Database,
  Cpu,
  Boxes,
  Stethoscope,
  History,
  SlidersHorizontal,
  HeartPulse,
  ArrowLeft,
} from "lucide-react";
import { useAppState } from "../state/AppState";
import Tooltip from "./Tooltip";

const NAV_ITEMS = [
  { to: "/gpai", label: "Overview", icon: Activity, tip: "Track pipeline progress across all five steps at a glance." },
  { to: "/gpai/data", label: "1. Data Ingestion", icon: Database, tip: "Load or generate the medical case dataset that powers the diagnostician." },
  { to: "/gpai/process", label: "2. Process & Embed", icon: Cpu, tip: "Convert cases into vector embeddings using your chosen AI engine." },
  { to: "/gpai/clusters", label: "3. Cluster Visualization", icon: Boxes, tip: "Visually explore how similar cases group together in embedding space." },
  { to: "/gpai/train", label: "4. Train Model", icon: SlidersHorizontal, tip: "Fit a retrieval/classification model on the embedded case data." },
  { to: "/gpai/diagnose", label: "5. Diagnose", icon: Stethoscope, tip: "Describe symptoms and get AI-assisted differential diagnosis suggestions." },
  { to: "/gpai/history", label: "Search History & Analytics", icon: History, tip: "Review past queries and analytics on diagnosis patterns." },
];

function StatusPill({ label, active }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
        active
          ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30"
          : "bg-slate-800/70 text-slate-400 ring-1 ring-slate-700"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-emerald-400" : "bg-slate-500"}`} />
      {label}
    </span>
  );
}

export default function Sidebar() {
  const { status } = useAppState();

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col overflow-y-auto border-r border-slate-800/70 bg-slate-950/80 px-4 py-6">
      <div className="mb-4 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-400 to-purple-500 shadow-glow">
          <HeartPulse className="h-6 w-6 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="truncate text-sm font-semibold leading-tight text-white">GP Assistant</p>
            <Tooltip
              accent="brand"
              title="GP Assistant Diagnostician"
              content="An end-to-end AI pipeline that ingests medical cases, embeds and clusters them, trains a model, and gives symptom-based diagnosis suggestions."
            />
          </div>
          <p className="text-xs text-slate-400">Diagnostician Console</p>
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
              end={to === "/gpai"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 pr-8 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-gradient-to-r from-brand-500/20 to-purple-500/10 text-white ring-1 ring-brand-500/30"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{label}</span>
            </NavLink>
            {tip && (
              <span className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-100">
                <Tooltip accent="brand" title={label} content={tip} />
              </span>
            )}
          </div>
        ))}
      </nav>

      <div className="mt-6 space-y-2 rounded-2xl border border-slate-800/70 bg-slate-900/50 p-3">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Pipeline Status
        </p>
        <div className="flex flex-wrap gap-1.5">
          <StatusPill label={`Data ${status.rows ? `(${status.rows})` : ""}`} active={status.rows > 0} />
          <StatusPill label="Embedded" active={status.processed} />
          <StatusPill label="Clustered" active={status.has_clusters} />
          <StatusPill label="Trained" active={status.trained} />
        </div>
        <p className="pt-1 text-[11px] text-slate-500">
          Engine: <span className="text-slate-300">{status.provider}</span>
        </p>
      </div>

      <p className="mt-4 px-2 text-[10px] leading-relaxed text-slate-600">
        Educational demo only — not medical advice. Always consult a qualified professional.
      </p>
    </aside>
  );
}
