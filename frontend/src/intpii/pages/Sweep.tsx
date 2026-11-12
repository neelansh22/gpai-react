import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { pct } from "../ui";
import type { Dataset, Mode, SweepPoint } from "../types";

export function Sweep({ datasets }: { datasets: Dataset[] }) {
  const [dataset, setDataset] = useState("synthetic");
  const [mode, setMode] = useState<Mode>("hybrid");
  const [points, setPoints] = useState<SweepPoint[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const run = async () => {
    setBusy(true); setErr("");
    try { setPoints((await api.sweep(dataset, mode, 300)).points); } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };
  const data = points?.map((p) => ({ threshold: p.threshold, Recall: p.overall.overlap.recall, Precision: p.overall.overlap.precision, F1: p.overall.overlap.f1 }));
  return (
    <section className="card">
      <h2>Threshold sweep</h2>
      <p className="muted">Runs the model once at a low floor, then filters by score for each threshold. This is an approximation of re-running at each value; confirm your chosen threshold on the Evaluate tab.</p>
      <div className="controls">
        <label>Dataset<select value={dataset} onChange={(e) => setDataset(e.target.value)}>{datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
        <label>Detector<select value={mode} onChange={(e) => setMode(e.target.value as Mode)}><option value="hybrid">hybrid</option><option value="gliner">model only</option></select></label>
        <button className="primary" onClick={run} disabled={busy}>{busy ? "Sweeping…" : "Run sweep"}</button>
      </div>
      {err && <div className="error">{err}</div>}
      {data && (
        <>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334" /><XAxis dataKey="threshold" /><YAxis domain={[0, 1]} tickFormatter={(v) => `${v * 100}%`} />
              <Tooltip formatter={(v) => pct(Number(v))} contentStyle={{ background: "#1b1d2a", border: "1px solid #334" }} /><Legend />
              <ReferenceLine y={0.95} stroke="#f59e0b" strokeDasharray="4 4" label="recall target" />
              <Line dataKey="Recall" stroke="#10b981" strokeWidth={2} /><Line dataKey="Precision" stroke="#a78bfa" strokeWidth={2} /><Line dataKey="F1" stroke="#3b82f6" strokeDasharray="3 3" />
            </LineChart>
          </ResponsiveContainer>
          <table><thead><tr><th>Threshold</th><th>Recall</th><th>Precision</th><th>F1</th></tr></thead>
            <tbody>{data.map((d) => <tr key={d.threshold}><td>{d.threshold}</td><td>{pct(d.Recall)}</td><td>{pct(d.Precision)}</td><td>{d.F1.toFixed(2)}</td></tr>)}</tbody></table>
        </>)}
    </section>
  );
}
