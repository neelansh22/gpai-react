import { useEffect, useState } from "react";
import { api } from "../api";
import { pct } from "../ui";
import type { Health, Run } from "../types";

const STAGES = [
  ["Ingest", "Files or stdin lines, one record each"],
  ["Chunk", "1200 chars, 200 overlap, offsets kept"],
  ["Rules", "Regex: email, phone, age, postcode"],
  ["Model", "GLiNER ONNX int8 scores spans"],
  ["Merge", "Union; rule wins for EMAIL/PHONE/AGE"],
  ["Validate", "Every span must be an exact substring"],
  ["Output", "JSON lines: label, offsets, score"],
];

export function About({ health }: { health: Health | null }) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api.runs().then(setRuns).catch((e) => setError(String(e))); }, []);
  return (
    <>
      <section className="card">
        <h2>Pipeline</h2>
        <div className="pipeline">{STAGES.map(([n, d], i) => <div className="step" key={n}><b>{i + 1}. {n}</b><span>{d}</span></div>)}</div>
        {health && <p className="muted">Model SHA-256 (verified on load): <code>{health.model_sha256.slice(0, 16)}…</code> · onnxruntime {health.onnxruntime} · targets: recall ≥ {pct(health.recall_target)}, p95 ≤ {health.latency_target_s * 1000} ms</p>}
      </section>
      <section className="card">
        <h2>Saved runs</h2>
        {error && <div className="error">{error}</div>}
        <table><thead><tr><th>File</th><th>Recall</th><th>Precision</th><th>F1</th><th>p50 ms</th><th>p95 ms</th></tr></thead>
          <tbody>{runs.map((r) => <tr key={r.file}><td>{r.file}</td><td>{pct(r.recall)}</td><td>{pct(r.precision)}</td><td>{r.f1.toFixed(2)}</td><td>{(r.p50_s * 1000).toFixed(1)}</td><td>{(r.p95_s * 1000).toFixed(1)}</td></tr>)}</tbody></table>
        <p className="muted">Overlap-mode, all entities. Summaries are held in service memory and are lost on restart; document text is not saved with them.</p>
      </section>
    </>
  );
}
