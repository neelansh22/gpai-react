import { useState } from "react";
import { NavLink } from "react-router-dom";
import { Wand2, MessageSquareText, Network, PencilRuler, Database, Sparkles, ArrowLeft, Wifi, WifiOff } from "lucide-react";
import { useSdodState } from "../state/SdodState";

const NAV_ITEMS = [
  { to: "/sdod", label: "Overview", icon: Wand2 },
  { to: "/sdod/intent", label: "1. Define Intent", icon: MessageSquareText },
  { to: "/sdod/schema", label: "2. Build Schema", icon: Network },
  { to: "/sdod/editor", label: "3. Edit Schema", icon: PencilRuler },
  { to: "/sdod/generate", label: "4. Generate Data", icon: Database },
  { to: "/sdod/augment", label: "5. Augment & Explore", icon: Sparkles },
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

export default function SdodSidebar() {
  const { status, setLlmConfig, notify } = useSdodState();
  const llm = status.llm || { provider: "offline", connected: false, last_error: null };
  const [provider, setProvider] = useState(llm.provider || "offline");
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const data = await setLlmConfig(provider, apiKey || undefined);
      if (provider !== "offline" && !data.connected) {
        notify(data.last_error || "Could not connect to provider", "error");
      } else {
        notify(provider === "offline" ? "Switched to offline mode" : `Connected to ${provider}`, "success");
      }
      setApiKey("");
    } catch (e) {
      notify("Failed to update connector", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-slate-800/70 bg-slate-950/80 px-4 py-6">
      <div className="mb-4 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 shadow-glow">
          <Wand2 className="h-6 w-6 text-white" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight text-white">Synthetic Data</p>
          <p className="text-xs text-slate-400">On Demand</p>
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
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/sdod"}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                isActive
                  ? "bg-gradient-to-r from-emerald-500/20 to-teal-500/10 text-white ring-1 ring-emerald-500/30"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-6 space-y-2 rounded-2xl border border-slate-800/70 bg-slate-900/50 p-3">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Pipeline Status
        </p>
        <div className="flex flex-wrap gap-1.5">
          <StatusPill label="Intent" active={status.has_answers} />
          <StatusPill label={`Schema${status.table_count ? ` (${status.table_count})` : ""}`} active={status.has_schema} />
          <StatusPill label="Data" active={status.has_data} />
          <StatusPill label="Augmented" active={status.has_augmented} />
        </div>
        {status.domain && (
          <p className="pt-1 text-[11px] text-slate-500">
            Domain: <span className="text-slate-300 capitalize">{status.domain}</span>
          </p>
        )}
      </div>

      <div className="mt-4 space-y-2 rounded-2xl border border-slate-800/70 bg-slate-900/50 p-3">
        <div className="mb-1 flex items-center justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            AI Connector
          </p>
          {llm.connected ? (
            <Wifi className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <WifiOff className="h-3.5 w-3.5 text-slate-500" />
          )}
        </div>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-2 py-1.5 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
        >
          <option value="offline">Offline (template engine)</option>
          <option value="openai">OpenAI (gpt-4o-mini)</option>
          <option value="gemini">Google Gemini</option>
        </select>
        {provider !== "offline" && (
          <input
            type="password"
            placeholder={llm.provider === provider && llm.connected ? "API key saved" : "API key"}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-2 py-1.5 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
          />
        )}
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full rounded-lg bg-emerald-500/90 px-2 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-60"
        >
          {saving ? "Saving..." : "Apply"}
        </button>
        <p className="pt-0.5 text-[10px] text-slate-500">
          {llm.connected
            ? `Online mode active (${llm.provider}).`
            : "Offline mode — deterministic, no API key required."}
        </p>
      </div>
    </aside>
  );
}
