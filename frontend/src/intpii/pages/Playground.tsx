import { useState } from "react";
import { api } from "../api";
import { Highlight, Legend } from "../ui";
import { Analytics, matchesFocus, type Focus, type Stage as AStage } from "../Analytics";
import { LABELS, type Chunk, type Entity, type Label, type Mode, type Trace } from "../types";

const SAMPLE = `Hi team,

Please send the signed form to Dr. Priya Raman, 14B Mill Lane, Leeds LS1 4AP. She is 41 years old and can be reached on +44 113 496 0123 or priya.raman@example.org.

Order #48213 has 12 items. Rose Street Cafe will cater on April 9.`;

type Stage = "Regex" | "Model" | "Merge" | "Final";

export function Playground() {
  const [text, setText] = useState(SAMPLE);
  const [mode, setMode] = useState<Mode>("hybrid");
  const [threshold, setThreshold] = useState(0.3);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [resultText, setResultText] = useState("");
  const [stage, setStage] = useState<Stage>("Final");
  const [focus, setFocus] = useState<Focus>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const run = async () => {
    setBusy(true); setErr("");
    try { setTrace(await api.extract(text, mode, threshold)); setResultText(text); setFocus(null); } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };

  const stageEntities = (t: Trace): Entity[] => {
    const pick = (f: (c: Chunk) => Entity[]) => t.chunks.flatMap(f);
    if (stage === "Regex") return pick((c) => c.regex);
    if (stage === "Model") return pick((c) => c.model);
    if (stage === "Merge") return pick((c) => c.merged);
    return t.entities;
  };

  const countBy = (es: Entity[]) => LABELS.reduce((o, l) => ({ ...o, [l]: es.filter((e) => e.label === l).length }), {} as Partial<Record<Label, number>>);
  const stages = (t: Trace): AStage[] => [
    { name: "Rules", counts: countBy(t.chunks.flatMap((c) => c.regex)) },
    { name: "Model", counts: countBy(t.chunks.flatMap((c) => c.model)) },
    { name: "Final", counts: countBy(t.entities) },
  ];
  const shown = (es: Entity[]) => es.filter((e) => matchesFocus(focus, e.label, e.text ?? ""));

  return (
    <div className="grid2">
      <div className="stack">
      <section className="card">
        <h2>Input</h2>
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={14} />
        <div className="controls">
          <label>Detector
            <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
              <option value="hybrid">hybrid (rules + model)</option><option value="gliner">model only</option><option value="regex">rules only</option>
            </select>
          </label>
          <label>Threshold {threshold.toFixed(2)}
            <input type="range" min={0.05} max={0.9} step={0.05} value={threshold} onChange={(e) => setThreshold(+e.target.value)} />
          </label>
          <button className="primary" onClick={run} disabled={busy || !text.trim()}>{busy ? "Running…" : "Extract"}</button>
        </div>
        {err && <div className="error">{err}</div>}
      </section>

      <section className="card">
        <h2>Analytics <small>interactive: click a chip or bubble to focus the result</small></h2>
        {!trace ? <p className="muted">Run the extractor to see clusters, confidence and which stage found what.</p> : (
          <Analytics items={trace.entities.map((e) => ({ label: e.label, text: e.text ?? "", score: e.score }))}
            chars={trace.chars} ms={trace.ms.total} stages={stages(trace)} focus={focus} onFocus={setFocus} />)}
      </section>
      </div>

      <section className="card">
        <h2>Result</h2>
        {!trace ? <p className="muted">Run the extractor to see entities and the pipeline stages.</p> : (
          <>
            <div className="pipeline">
              {[["Input", `${trace.chars} chars`], ["Chunking", `${trace.chunks.length} chunk(s)`],
                ["Regex", `${trace.chunks.reduce((n, c) => n + c.regex.length, 0)} spans · ${trace.ms.regex} ms`],
                ["Model", `${trace.chunks.reduce((n, c) => n + c.model.length, 0)} spans · ${trace.ms.model} ms`],
                ["Merge", `${trace.chunks.reduce((n, c) => n + c.merged.length, 0)} spans · ${trace.ms.merge} ms`],
                ["Final", `${trace.entities.length} entities · dedupe ${trace.ms.dedupe} ms`]].map(([name, info], i) => {
                const clickable = ["Regex", "Model", "Merge", "Final"].includes(name);
                return (
                  <div key={name} className={`step ${stage === name ? "sel" : ""} ${clickable ? "click" : ""}`}
                    onClick={() => clickable && setStage(name as Stage)}>
                    <b>{i + 1}. {name}</b><span>{info}</span>
                  </div>
                );
              })}
            </div>
            <p className="muted">Total {trace.ms.total} ms. Showing the <b>{stage}</b> stage. Click a step to compare.</p>
            <Legend />
            <Highlight text={resultText} entities={shown(stageEntities(trace))} />
            <table>
              <thead><tr><th>Label</th><th>Text</th><th>Offsets</th><th>Score</th></tr></thead>
              <tbody>{shown(trace.entities).map((e, i) => (
                <tr key={i}><td>{e.label}</td><td>{e.text}</td><td>{e.start}–{e.end}</td><td>{e.score?.toFixed(3)}</td></tr>))}</tbody>
            </table>
            {trace.chunks.length > 1 && (
              <details><summary>Chunks</summary>
                <table><thead><tr><th>#</th><th>Range</th><th>Regex</th><th>Model</th><th>Merged</th><th>ms (model)</th></tr></thead>
                  <tbody>{trace.chunks.map((c, i) => (
                    <tr key={i}><td>{i + 1}</td><td>{c.start}–{c.end}</td><td>{c.regex.length}</td><td>{c.model.length}</td><td>{c.merged.length}</td><td>{c.ms.model}</td></tr>))}</tbody></table>
              </details>)}
          </>)}
      </section>
    </div>
  );
}
