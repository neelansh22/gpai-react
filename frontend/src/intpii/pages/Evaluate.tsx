import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { Highlight, Legend as LabelLegend, pct } from "../ui";
import { LABELS, type Dataset, type EvalResult, type Health, type Mode } from "../types";

interface Props { datasets: Dataset[]; result: EvalResult | null; setResult: (r: EvalResult | null) => void; health: Health | null }

export function Evaluate({ datasets, result, setResult, health }: Props) {
  const [dataset, setDataset] = useState("synthetic");
  const [mode, setMode] = useState<Mode>("hybrid");
  const [threshold, setThreshold] = useState(0.3);
  const [n, setN] = useState(300);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [docIdx, setDocIdx] = useState(0);

  const run = async () => {
    setBusy(true); setErr("");
    try { setResult(await api.evaluate(dataset, mode, threshold, n)); setDocIdx(0); } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };

  const target = health?.recall_target ?? 0.95;
  const chart = result ? LABELS.map((l) => ({
    label: l, Recall: result.metrics[l].overlap.recall, Precision: result.metrics[l].overlap.precision,
    "Recall (exact)": result.metrics[l].exact.recall,
  })) : [];
  const all = result?.metrics.ALL;

  return (
    <>
      <section className="card">
        <h2>Run an evaluation</h2>
        <div className="controls">
          <label>Dataset
            <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
              {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </label>
          <label>Detector
            <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
              <option value="hybrid">hybrid</option><option value="gliner">model only</option><option value="regex">rules only</option>
            </select>
          </label>
          <label>Threshold {threshold.toFixed(2)}
            <input type="range" min={0.05} max={0.9} step={0.05} value={threshold} onChange={(e) => setThreshold(+e.target.value)} />
          </label>
          {dataset === "synthetic" && <label>Docs<input type="number" min={10} max={2000} value={n} onChange={(e) => setN(+e.target.value)} /></label>}
          <button className="primary" onClick={run} disabled={busy}>{busy ? "Evaluating…" : "Run evaluation"}</button>
        </div>
        {datasets.length === 1 && <p className="muted">The hosted demo evaluates synthetic data only. Large evaluations may take several minutes.</p>}
        {err && <div className="error">{err}</div>}
      </section>

      {result && all && (
        <>
          <div className="kpis">
            <Kpi title="Recall (overlap)" value={pct(all.overlap.recall)} ok={all.overlap.recall >= target} note={`target ${pct(target)}`} />
            <Kpi title="Precision (overlap)" value={pct(all.overlap.precision)} />
            <Kpi title="Recall (exact)" value={pct(all.exact.recall)} />
            <Kpi title="Latency p50 / p95" value={`${(result.latency.p50_s * 1000).toFixed(0)} / ${(result.latency.p95_s * 1000).toFixed(0)} ms`}
              ok={result.latency.p95_s <= (health?.latency_target_s ?? 1)} note="per document" />
            <Kpi title="Documents / gold entities" value={`${result.docs} / ${result.entities_gold}`} />
          </div>
          <section className="card">
            <h2>Per-entity performance</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334" />
                <XAxis dataKey="label" /><YAxis domain={[0, 1]} tickFormatter={(v) => `${v * 100}%`} />
                <Tooltip formatter={(v) => pct(Number(v))} contentStyle={{ background: "#1b1d2a", border: "1px solid #334" }} />
                <Legend /><ReferenceLine y={target} stroke="#f59e0b" strokeDasharray="4 4" label="recall target" />
                <Bar dataKey="Recall" fill="#10b981" /><Bar dataKey="Recall (exact)" fill="#3b82f6" /><Bar dataKey="Precision" fill="#a78bfa" />
              </BarChart>
            </ResponsiveContainer>
            <table>
              <thead><tr><th>Label</th><th>Gold</th><th>Found (TP)</th><th>Missed (FN)</th><th>False alarms (FP)</th><th>Recall</th><th>Precision</th><th>F1</th><th>Exact recall</th></tr></thead>
              <tbody>{[...LABELS, "ALL"].map((l) => { const m = result.metrics[l]; return (
                <tr key={l} className={l === "ALL" ? "total" : ""}><td>{l}</td><td>{m.overlap.tp + m.overlap.fn}</td><td>{m.overlap.tp}</td><td>{m.overlap.fn}</td><td>{m.overlap.fp}</td>
                  <td className={m.overlap.recall < target ? "bad" : ""}>{pct(m.overlap.recall)}</td><td>{pct(m.overlap.precision)}</td><td>{m.overlap.f1.toFixed(2)}</td><td>{pct(m.exact.recall)}</td></tr>); })}</tbody>
            </table>
            <p className="muted">Overlap = the right label on any overlapping range; exact = identical boundaries. Latency is detection only, excluding model load.</p>
          </section>
          <section className="card">
            <h2>Document viewer</h2>
            <div className="controls">
              <label>Document {docIdx + 1} / {result.documents.length}
                <input type="range" min={0} max={result.documents.length - 1} value={docIdx} onChange={(e) => setDocIdx(+e.target.value)} />
              </label>
            </div>
            <LabelLegend />
            <div className="grid2">
              <div><h3>Gold (expected)</h3><Highlight text={result.documents[docIdx].text} entities={result.documents[docIdx].gold} /></div>
              <div><h3>Predicted</h3><Highlight text={result.documents[docIdx].text} entities={result.documents[docIdx].pred} /></div>
            </div>
          </section>
        </>)}
    </>
  );
}

function Kpi({ title, value, ok, note }: { title: string; value: string; ok?: boolean; note?: string }) {
  return <div className={`kpi ${ok === undefined ? "" : ok ? "good" : "bad"}`}><span>{title}</span><b>{value}</b>{note && <small>{note}</small>}</div>;
}
