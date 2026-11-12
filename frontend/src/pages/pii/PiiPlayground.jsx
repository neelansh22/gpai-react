import { useMemo, useState } from "react";
import { ScanSearch, FileUp, Download, Loader2 } from "lucide-react";
import { Card, PageHeader, Button, Badge } from "../../components/ui";
import { Highlight, Legend, COLORS } from "../../components/PiiHighlight";
import { piiEndpoints } from "../../api/piiClient";

const SAMPLE = `Hi team,

Please send the signed form to Dr. Priya Raman, 14B Mill Lane, Leeds LS1 4AP. She is 41 years old and can be reached on +44 113 496 0123 or priya.raman@example.org.

Order #48213 has 12 items. Rose Street Cafe will cater on April 9.`;

const MODES = [
  { value: "hybrid", label: "Hybrid (rules + model)" },
  { value: "gliner", label: "Model only" },
  { value: "regex", label: "Rules only" },
];

const STAGES = ["Regex", "Model", "Merge", "Final"];
const STYLES = [
  { value: "box", label: "Black box" },
  { value: "label", label: "[LABEL] tag" },
  { value: "partial", label: "Partial mask" },
];

function TextTab() {
  const [text, setText] = useState(SAMPLE);
  const [mode, setMode] = useState("hybrid");
  const [threshold, setThreshold] = useState(0.3);
  const [trace, setTrace] = useState(null);
  const [stage, setStage] = useState("Final");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const run = async () => {
    setBusy(true);
    setErr("");
    try {
      const { data } = await piiEndpoints.extract(text, mode, threshold);
      setTrace(data);
    } catch (e) {
      setErr(e.response?.data?.detail ? String(e.response.data.detail) : e.message);
    } finally {
      setBusy(false);
    }
  };

  const stageEntities = useMemo(() => {
    if (!trace) return [];
    const pick = (fn) => trace.chunks.flatMap(fn);
    if (stage === "Regex") return pick((c) => c.regex);
    if (stage === "Model") return pick((c) => c.model);
    if (stage === "Merge") return pick((c) => c.merged);
    return trace.entities;
  }, [trace, stage]);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <h3 className="mb-3 font-semibold text-white">Input</h3>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={12}
          className="w-full rounded-xl border border-slate-700 bg-slate-950/70 p-3 font-mono text-sm text-slate-200 focus:border-rose-500 focus:outline-none"
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950/70 px-2 py-1.5 text-xs text-slate-200 focus:border-rose-500 focus:outline-none"
          >
            {MODES.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            Threshold {threshold.toFixed(2)}
            <input
              type="range"
              min={0.05}
              max={0.9}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(+e.target.value)}
              className="accent-rose-500"
            />
          </label>
          <Button onClick={run} disabled={busy || !text.trim()}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
            {busy ? "Running…" : "Extract"}
          </Button>
        </div>
        {err && <p className="mt-2 text-sm text-rose-300">{err}</p>}
      </Card>

      <Card>
        <h3 className="mb-3 font-semibold text-white">Result</h3>
        {!trace ? (
          <p className="text-sm text-slate-500">Run the extractor to see entities and the pipeline stages.</p>
        ) : (
          <>
            <div className="mb-3 flex flex-wrap gap-2">
              {STAGES.map((s) => (
                <button
                  key={s}
                  onClick={() => setStage(s)}
                  className={`rounded-full px-3 py-1 text-xs font-medium ring-1 transition ${
                    stage === s ? "bg-rose-500/20 text-rose-200 ring-rose-500/40" : "bg-slate-800/70 text-slate-400 ring-slate-700 hover:text-slate-200"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
            <p className="mb-2 text-xs text-slate-500">
              {trace.chars} chars · {trace.chunks.length} chunk(s) · {trace.entities.length} final entities · {trace.ms.total} ms total
            </p>
            <Legend />
            <div className="max-h-72 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <Highlight text={text} entities={stageEntities} />
            </div>
            <div className="mt-3 max-h-48 overflow-y-auto rounded-xl border border-slate-800">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Label</th>
                    <th className="px-3 py-2">Text</th>
                    <th className="px-3 py-2">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {trace.entities.map((e, i) => (
                    <tr key={i} className="text-slate-300">
                      <td className="px-3 py-1.5">
                        <Badge>{e.label}</Badge>
                      </td>
                      <td className="px-3 py-1.5 font-mono">{e.text}</td>
                      <td className="px-3 py-1.5">{e.score?.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

function FileTab() {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState("hybrid");
  const [threshold, setThreshold] = useState(0.3);
  const [style, setStyle] = useState("box");
  const [res, setRes] = useState(null);
  const [rejected, setRejected] = useState(new Set());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const spansByUnit = useMemo(() => {
    const m = new Map();
    (res?.spans ?? []).forEach((s) => m.set(s.unit, [...(m.get(s.unit) ?? []), s]));
    return m;
  }, [res]);

  const analyze = async () => {
    if (!file) return;
    setBusy(true);
    setErr("");
    try {
      if (res) await piiEndpoints.redactDelete(res.doc_id).catch(() => {});
      const { data } = await piiEndpoints.redactAnalyze(file, mode, threshold);
      setRes(data);
      setRejected(new Set());
    } catch (e) {
      setErr(e.response?.data?.detail ? String(e.response.data.detail) : e.message);
      setRes(null);
    } finally {
      setBusy(false);
    }
  };

  const toggle = (id) =>
    setRejected((r) => {
      const n = new Set(r);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const download = async () => {
    if (!res) return;
    setBusy(true);
    setErr("");
    try {
      const { data, headers } = await piiEndpoints.redactExport(res.doc_id, style, [], [...rejected]);
      const match = /filename="([^"]+)"/.exec(headers["content-disposition"] || "");
      const url = URL.createObjectURL(data);
      const a = Object.assign(document.createElement("a"), { href: url, download: match ? match[1] : "redacted" });
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr(e.response?.data?.detail ? String(e.response.data.detail) : e.message);
    } finally {
      setBusy(false);
    }
  };

  const keptCount = (res?.spans.length || 0) - rejected.size;

  return (
    <Card>
      <h3 className="mb-3 font-semibold text-white">Upload a document</h3>
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".txt,.md,.csv,.json,.log,.docx,.pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-xs text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-800 file:px-3 file:py-1.5 file:text-xs file:text-slate-200 hover:file:bg-slate-700"
        />
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950/70 px-2 py-1.5 text-xs text-slate-200 focus:border-rose-500 focus:outline-none"
        >
          {MODES.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-xs text-slate-400">
          Threshold {threshold.toFixed(2)}
          <input type="range" min={0.05} max={0.9} step={0.05} value={threshold} onChange={(e) => setThreshold(+e.target.value)} className="accent-rose-500" />
        </label>
        <Button onClick={analyze} disabled={busy || !file}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
          {busy ? "Analyzing…" : "Detect PII"}
        </Button>
      </div>
      {err && <p className="mt-2 text-sm text-rose-300">{err}</p>}

      {res && (
        <>
          <p className="mt-4 mb-2 text-xs text-slate-500">
            {res.filename} · {res.spans.length} span(s) detected in {res.ms} ms · click a highlight to keep/redact it ·{" "}
            <span className="text-slate-300">{keptCount} will be redacted</span>
          </p>
          <Legend />
          <div className="max-h-96 space-y-2 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            {res.units.map((u) => (
              <div key={u.id} className="whitespace-pre-wrap break-words font-mono text-sm leading-relaxed text-slate-200">
                {renderUnit(u.text, spansByUnit.get(u.id) ?? [], rejected, toggle)}
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-950/70 px-2 py-1.5 text-xs text-slate-200 focus:border-rose-500 focus:outline-none"
            >
              {STYLES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <Button onClick={download} disabled={busy}>
              <Download className="h-4 w-4" />
              Export redacted copy
            </Button>
          </div>
        </>
      )}
    </Card>
  );
}

function renderUnit(text, spans, rejected, toggle) {
  const sorted = [...spans].sort((a, b) => a.start - b.start || b.end - a.end);
  const parts = [];
  let pos = 0;
  sorted.forEach((s) => {
    if (s.start < pos) return;
    if (s.start > pos) parts.push(text.slice(pos, s.start));
    const off = rejected.has(s.id);
    parts.push(
      <mark
        key={s.id}
        onClick={() => toggle(s.id)}
        className="cursor-pointer rounded px-0.5"
        style={{
          background: off ? "transparent" : "#000",
          color: off ? "inherit" : "#fff",
          textDecoration: off ? "line-through" : "none",
          outline: `2px solid ${COLORS[s.label]}`,
        }}
        title={`${s.label} (${s.score.toFixed(2)}) — click to ${off ? "redact" : "keep"}`}
      >
        {text.slice(s.start, s.end)}
      </mark>
    );
    pos = s.end;
  });
  parts.push(text.slice(pos));
  return parts;
}

export default function PiiPlayground() {
  const [tab, setTab] = useState("text");

  return (
    <div>
      <PageHeader
        icon={ScanSearch}
        title="Detect & Redact"
        subtitle="Run the hybrid detector on raw text, or upload a document for interactive, in-memory redaction."
        accent="rose"
      />
      <div className="mb-5 flex gap-2">
        <button
          onClick={() => setTab("text")}
          className={`rounded-xl px-4 py-2 text-sm font-medium ring-1 transition ${
            tab === "text" ? "bg-rose-500/20 text-rose-200 ring-rose-500/40" : "bg-slate-800/70 text-slate-400 ring-slate-700"
          }`}
        >
          Text
        </button>
        <button
          onClick={() => setTab("file")}
          className={`rounded-xl px-4 py-2 text-sm font-medium ring-1 transition ${
            tab === "file" ? "bg-rose-500/20 text-rose-200 ring-rose-500/40" : "bg-slate-800/70 text-slate-400 ring-slate-700"
          }`}
        >
          File redaction
        </button>
      </div>
      {tab === "text" ? <TextTab /> : <FileTab />}
    </div>
  );
}
