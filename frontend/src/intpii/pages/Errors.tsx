import { useMemo, useState } from "react";
import { COLORS, LABELS, type EvalResult } from "../types";

export function Errors({ result }: { result: EvalResult | null }) {
  const [type, setType] = useState<"all" | "fn" | "fp">("all");
  const [label, setLabel] = useState<string>("all");
  const [showN, setShowN] = useState(50);
  const items = useMemo(() => (result?.errors ?? []).filter((e) => (type === "all" || e.type === type) && (label === "all" || e.label === label)), [result, type, label]);

  if (!result) return <p className="muted">Run an evaluation first (Evaluate tab); its misses and false alarms appear here.</p>;
  const fn = result.errors.filter((e) => e.type === "fn").length;
  return (
    <section className="card">
      <h2>Error review <small>{fn} missed · {result.errors.length - fn} false alarms</small></h2>
      <div className="controls">
        <label>Type<select value={type} onChange={(e) => setType(e.target.value as typeof type)}>
          <option value="all">all</option><option value="fn">missed (false negatives)</option><option value="fp">false alarms (false positives)</option></select></label>
        <label>Label<select value={label} onChange={(e) => setLabel(e.target.value)}>
          <option value="all">all</option>{LABELS.map((l) => <option key={l}>{l}</option>)}</select></label>
      </div>
      <p className="muted">Showing {Math.min(showN, items.length)} of {items.length}. Misses matter most for a recall-first system.</p>
      {items.slice(0, showN).map((e, i) => (
        <div key={i} className={`err ${e.type}`}>
          <span className="tag" style={{ background: COLORS[e.label] }}>{e.label}</span>
          <span className="kind">{e.type === "fn" ? "MISSED" : "FALSE ALARM"}</span>
          <span className="ctx">…{e.context.before}<mark className={e.type}>{e.context.span}</mark>{e.context.after}…</span>
          <small>doc {e.doc + 1}{e.score !== undefined ? ` · score ${e.score.toFixed(2)}` : ""}</small>
        </div>))}
      {items.length > showN && <button onClick={() => setShowN(showN + 50)}>Show more</button>}
    </section>
  );
}
