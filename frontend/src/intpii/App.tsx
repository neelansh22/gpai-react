import { useEffect, useState } from "react";
import { api, modelSize } from "./api";
import type { Dataset, EvalResult, Health } from "./types";
import { Playground } from "./pages/Playground";
import { Evaluate } from "./pages/Evaluate";
import { Errors } from "./pages/Errors";
import { Sweep } from "./pages/Sweep";
import { About } from "./pages/About";
import { Redact } from "./pages/Redact";
import { Link } from "react-router-dom";
import "./style.css";

const TABS = ["Redact", "Playground", "Evaluate", "Errors", "Threshold sweep", "Pipeline & runs"] as const;
type Tab = (typeof TABS)[number];

export default function App() {
  const [tab, setTab] = useState<Tab>("Redact");
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState("");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [result, setResult] = useState<EvalResult | null>(null);
  const [size, setSize] = useState(modelSize.get());

  useEffect(() => {
    let stop = false;
    const poll = async () => {
      try {
        const [h, d] = await Promise.all([api.health(), api.datasets()]);
        if (!stop) { setHealth(h); setDatasets(d); setError(""); }
      } catch (e) {
        if (!stop) setError(String(e));
      }
    };
    poll();
    const timer = window.setInterval(poll, 30000);
    return () => { stop = true; window.clearInterval(timer); };
  }, []);

  return (
    <div className="intpii-console">
    <div className="app">
      <header>
        <Link to="/" className="portfolio-back">← Portfolio</Link>
        <h1>int-pii <small>pilot console</small></h1>
        <span className="badge warn">Hosted demo · use synthetic data only</span>
        <span className={`badge ${health?.model_loaded ? "ok" : "warn"}`}>
          {error ? "API unavailable" : health ? (health.model_loaded ? "model ready" : "model loads on first use") : "connecting…"}
        </span>
        {health && health.sizes.length > 1 && (
          <label className="badge">Model size:{" "}
            <select value={size} onChange={(e) => { modelSize.set(e.target.value); setSize(e.target.value); }}>
              {health.sizes.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>)}
      </header>
      <nav>{TABS.map((t) => <button key={t} className={t === tab ? "active" : ""} onClick={() => setTab(t)}>{t}</button>)}</nav>
      {error && <div className="error">Cannot reach the PII service: {error}</div>}
      <main>
        {tab === "Redact" && <Redact />}
        {tab === "Playground" && <Playground />}
        {tab === "Evaluate" && <Evaluate datasets={datasets} result={result} setResult={setResult} health={health} />}
        {tab === "Errors" && <Errors result={result} />}
        {tab === "Threshold sweep" && <Sweep datasets={datasets} />}
        {tab === "Pipeline & runs" && <About health={health} />}
      </main>
    </div>
    </div>
  );
}
