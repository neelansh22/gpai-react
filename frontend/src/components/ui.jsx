export function Card({ children, className = "" }) {
  return (
    <div className={`glass-panel rounded-2xl p-5 shadow-lg shadow-black/20 ${className}`}>{children}</div>
  );
}

export function PageHeader({ icon: Icon, title, subtitle, right }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500/20 to-purple-500/20 ring-1 ring-brand-500/30">
            <Icon className="h-5 w-5 text-brand-300" />
          </div>
        )}
        <div>
          <h1 className="text-xl font-semibold text-white">{title}</h1>
          {subtitle && <p className="mt-0.5 text-sm text-slate-400">{subtitle}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}

export function Metric({ label, value, hint, accent = "brand" }) {
  const accentClass =
    {
      brand: "text-brand-300",
      emerald: "text-emerald-300",
      amber: "text-amber-300",
      rose: "text-rose-300",
      purple: "text-purple-300",
    }[accent] || "text-brand-300";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accentClass}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export function Button({ children, variant = "primary", className = "", ...props }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50";
  const variants = {
    primary:
      "bg-gradient-to-r from-brand-500 to-purple-500 text-white shadow-lg shadow-brand-500/20 hover:shadow-brand-500/40 hover:-translate-y-0.5",
    secondary: "bg-slate-800 text-slate-200 hover:bg-slate-700 ring-1 ring-slate-700",
    ghost: "text-slate-300 hover:bg-slate-800/60",
    danger: "bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30 hover:bg-rose-500/25",
  };
  return (
    <button className={`${base} ${variants[variant] || variants.primary} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function Badge({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-800 text-slate-300 ring-slate-700",
    green: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
    amber: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
    red: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${tones[tone] || tones.slate}`}>
      {children}
    </span>
  );
}

export function Spinner({ className = "" }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
    />
  );
}
