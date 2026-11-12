import { useMemo, useState } from "react";
import { redact } from "../api";
import { Legend } from "../ui";
import { Analytics, matchesFocus, type Focus } from "../Analytics";
import { COLORS, LABELS, type AddedSpan, type Label, type Mode, type RedactAnalysis, type RedactSpan, type RedactStyle } from "../types";

const ACCEPT = ".txt,.md,.csv,.json,.log,.docx,.pdf";

function Unit({ unit, text, spans, manual, rejected, focus, toggle, remove, onSelect }: {
  focus: Focus; unit: number; text: string; spans: RedactSpan[]; manual: Set<string>; rejected: Set<string>;
  toggle: (id: string) => void; remove: (id: string) => void; onSelect: (unit: number, a: number, b: number) => void;
}) {
  const parts: React.ReactNode[] = [];
  const plain = (a: number, b: number) => b > a && parts.push(<span key={`p${a}`} data-s={a}>{text.slice(a, b)}</span>);
  let pos = 0;
  [...spans].sort((a, b) => a.start - b.start || b.end - a.end).forEach((s) => {
    if (s.start < pos) return;
    plain(pos, s.start);
    const isManual = manual.has(s.id);
    const off = rejected.has(s.id);
    parts.push(
      <mark key={s.id} onClick={() => (isManual ? remove(s.id) : toggle(s.id))}
        title={isManual ? `${s.label} (added by you) - click to remove` : `${s.label} (${s.score.toFixed(2)}) - click to ${off ? "redact" : "keep"}`}
        style={{ cursor: "pointer", background: off ? "transparent" : "#000", color: off ? "inherit" : "#fff",
          opacity: matchesFocus(focus, s.label, s.text) ? 1 : 0.25,
          outline: `2px ${isManual ? "dashed" : "solid"} ${COLORS[s.label]}`, textDecoration: off ? "line-through" : "none", borderRadius: 3 }}>
        <span data-s={s.start}>{text.slice(s.start, s.end)}</span><sup style={{ color: COLORS[s.label] }}>{s.label}{isManual ? "+" : ""}</sup>
      </mark>);
    pos = s.end;
  });
  plain(pos, text.length);
  const handle = (e: React.MouseEvent<HTMLDivElement>) => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.anchorNode || !sel.focusNode) return;
    if (!e.currentTarget.contains(sel.anchorNode) || !e.currentTarget.contains(sel.focusNode)) return;
    const at = (n: Node, o: number) => {
      const el = (n.nodeType === 3 ? n.parentElement : null)?.closest("[data-s]") as HTMLElement | null;
      return el ? +(el.dataset.s as string) + o : null;
    };
    const a = at(sel.anchorNode, sel.anchorOffset), b = at(sel.focusNode, sel.focusOffset);
    if (a === null || b === null) { onSelect(unit, -1, -1); return; }
    onSelect(unit, Math.min(a, b), Math.max(a, b));
  };
  return <div className="doc" style={{ margin: "4px 0", padding: "4px 10px" }} onMouseUp={handle}>{parts}</div>;
}

export function Redact() {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<Mode>("hybrid");
  const [threshold, setThreshold] = useState(0.3);
  const [style, setStyle] = useState<RedactStyle>("box");
  const [added, setAdded] = useState<AddedSpan[]>([]);
  const [pending, setPending] = useState<AddedSpan | null>(null);
  const [pendingLabel, setPendingLabel] = useState<Label>("PERSON");
  const [res, setRes] = useState<RedactAnalysis | null>(null);
  const [rejected, setRejected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [focus, setFocus] = useState<Focus>(null);
  const [excluded, setExcluded] = useState<Set<Label>>(new Set());

  const manualSpans: RedactSpan[] = useMemo(() => added.map((a) => ({
    id: `m:${a.unit}:${a.start}:${a.end}`, unit: a.unit, label: a.label, start: a.start, end: a.end,
    text: res?.units.find((u) => u.id === a.unit)?.text.slice(a.start, a.end) ?? "", score: 1 })), [added, res]);
  const manualIds = useMemo(() => new Set(manualSpans.map((s) => s.id)), [manualSpans]);

  const byUnit = useMemo(() => {
    const m = new Map<number, RedactSpan[]>();
    [...(res?.spans ?? []), ...manualSpans].forEach((s) => m.set(s.unit, [...(m.get(s.unit) ?? []), s]));
    return m;
  }, [res, manualSpans]);

  // Spans that will NOT be redacted: individually kept, or in an excluded category.
  const off = useMemo(() => new Set([...rejected,
    ...[...(res?.spans ?? []), ...manualSpans].filter((s) => excluded.has(s.label)).map((s) => s.id)]), [rejected, excluded, res, manualSpans]);

  const totals = useMemo(() => {
    const c: Record<string, number> = {};
    [...(res?.spans ?? []), ...manualSpans].forEach((s) => { c[s.label] = (c[s.label] ?? 0) + 1; });
    return c;
  }, [res, manualSpans]);
  const redactCount = useMemo(() => [...(res?.spans ?? []), ...manualSpans].filter((s) => !off.has(s.id)).length, [res, manualSpans, off]);
  const toggleLabel = (l: Label) => setExcluded((x) => { const n = new Set(x); if (n.has(l)) n.delete(l); else n.add(l); return n; });

  const analyze = async () => {
    if (!file) return;
    setBusy(true); setErr("");
    try {
      if (res) await redact.discard(res.doc_id);
      setRes(await redact.analyze(file, mode, threshold)); setRejected(new Set()); setExcluded(new Set()); setAdded([]); setPending(null); setFocus(null);
    } catch (e) { setErr(String(e)); setRes(null); } finally { setBusy(false); }
  };

  const toggle = (id: string) => setRejected((r) => { const n = new Set(r); if (n.has(id)) n.delete(id); else n.add(id); return n; });

  const download = async () => {
    if (!res) return;
    setBusy(true); setErr("");
    try {
      const { blob, name } = await redact.exportFile(res.doc_id, style, [...rejected, ...(res.spans ?? []).filter((s) => excluded.has(s.label)).map((s) => s.id)],
        added.filter((a) => !excluded.has(a.label)));
      const url = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement("a"), { href: url, download: name });
      a.click(); URL.revokeObjectURL(url);
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };

  const onSelect = (unit: number, a: number, b: number) => {
    const text = res?.units.find((u) => u.id === unit)?.text ?? "";
    if (a < 0) { setPending(null); setErr("Select plain document text only (not the label tags)."); return; }
    const lead = text.slice(a, b).length - text.slice(a, b).trimStart().length;
    const s = a + lead, e = s + text.slice(s, b).trim().length;
    setErr("");
    setPending(e > s ? { unit, start: s, end: e, label: pendingLabel } : null);
  };
  const addPending = () => {
    if (!pending) return;
    const dup = added.some((x) => x.unit === pending.unit && x.start === pending.start && x.end === pending.end);
    if (!dup) setAdded([...added, { ...pending, label: pendingLabel }]);
    setPending(null); window.getSelection()?.removeAllRanges();
  };

  const discard = async () => {
    try {
      if (res) await redact.discard(res.doc_id);
      setRes(null); setRejected(new Set()); setExcluded(new Set()); setAdded([]); setPending(null); setErr("");
    } catch (e) { setErr(String(e)); }
  };

  const items = useMemo(() => [...(res?.spans ?? []), ...manualSpans].filter((s) => !off.has(s.id))
    .map((s) => ({ label: s.label, text: s.text, score: s.score })), [res, off, manualSpans]);
  const chars = res?.units.reduce((n, u) => n + u.text.length, 0) ?? 0;

  return (
    <div className="grid2">
      <div className="stack">
      <section className="card">
        <h2>Redact a document <small>.txt · .docx · .pdf</small></h2>
        <div className="error" style={{ background: "#3a2a12", borderColor: "#7a5a20", color: "#fde68a" }}>
          Automated detection can miss personal data. Review every page before sharing the redacted file.
        </div>
        <div className="controls">
          <label>File
            <input type="file" accept={ACCEPT} onChange={(e) => { setFile(e.target.files?.[0] ?? null); }} />
          </label>
          <label>Detector
            <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
              <option value="hybrid">hybrid (rules + model)</option><option value="gliner">model only</option><option value="regex">rules only</option>
            </select>
          </label>
          <label>Threshold {threshold.toFixed(2)}
            <input type="range" min={0.05} max={0.9} step={0.05} value={threshold} onChange={(e) => setThreshold(+e.target.value)} />
          </label>
          <button className="primary" onClick={analyze} disabled={busy || !file}>{busy ? "Working…" : "Detect"}</button>
        </div>
        <p className="muted">Files are sent to the hosted service and held in its memory for approximately 30 minutes or until you click Discard. This is a public demo: use synthetic data only.</p>
        {err && <div className="error">{err}</div>}
      </section>

      {res && (
        <section className="card">
          <h2>Analytics <small>what will be redacted · click to spotlight it in the document</small></h2>
          <Analytics items={items} chars={chars} ms={res.ms} focus={focus} onFocus={setFocus} />
        </section>)}
      </div>

      {res ? (
        <section className="card">
          <h2>Review <small>{res.filename} · {res.kind} · detected in {res.ms} ms</small></h2>
          {res.warnings.map((w, i) => <div key={i} className="error" style={{ background: "#3a2a12", borderColor: "#7a5a20", color: "#fde68a" }}>{w}</div>)}
          <div className="controls">
            <b>{redactCount} to redact</b>
            {LABELS.filter((l) => totals[l]).map((l) => (
              <button key={l} className={`chip ${excluded.has(l) ? "excluded" : ""}`} style={{ borderColor: COLORS[l] }}
                title={excluded.has(l) ? `${l} is excluded - click to redact it again` : `Click to exclude all ${l} from redaction`}
                onClick={() => toggleLabel(l)}>
                <i style={{ background: COLORS[l] }} />{l} <b>{totals[l]}</b>{excluded.has(l) && " \u2298"}
              </button>))}
            <span className="muted">{rejected.size} kept{excluded.size > 0 && ` \u00b7 ${[...excluded].join(", ")} excluded`}</span>
            <label>Mask style
              <select value={style} onChange={(e) => setStyle(e.target.value as RedactStyle)}>
                <option value="box">black box</option><option value="label">label [PERSON]</option><option value="partial">partial mask</option>
              </select>
            </label>
            <button className="primary" onClick={download} disabled={busy}>Download redacted {res.kind === "text" ? "file" : res.kind}</button>
            <button onClick={discard}>Discard upload</button>
          </div>
          <p className="muted">Click a category chip above to exclude that whole category from redaction. Click a highlight to keep just that one. Select any text to add a redaction the detector missed; dashed highlights are yours, click to remove. {res.kind === "pdf" && "PDF output always uses black boxes."} </p>
          {pending && (
            <div className="controls" style={{ background: "#10111a", padding: 8, borderRadius: 8 }}>
              <span>Add <code>{res.units.find((u) => u.id === pending.unit)?.text.slice(pending.start, pending.end)}</code> as</span>
              <select value={pendingLabel} onChange={(e) => setPendingLabel(e.target.value as Label)}>
                {LABELS.map((l) => <option key={l}>{l}</option>)}
              </select>
              <button className="primary" onClick={addPending}>Add redaction</button>
              <button onClick={() => setPending(null)}>Cancel</button>
            </div>)}
          <Legend />
          <div style={{ maxHeight: 720, overflow: "auto" }}>
            {res.units.map((u) => (
              <div key={u.id}>
                {res.kind === "pdf" && <h3>Page {u.id + 1}</h3>}
                <Unit unit={u.id} text={u.text} spans={byUnit.get(u.id) ?? []} manual={manualIds} rejected={off} toggle={toggle}
                  focus={focus} remove={(id) => setAdded(added.filter((a) => `m:${a.unit}:${a.start}:${a.end}` !== id))} onSelect={onSelect} />
              </div>))}
          </div>
        </section>
      ) : (
        <section className="card">
          <h2>Review</h2>
          <ol className="muted" style={{ lineHeight: 1.9 }}>
            <li>Choose a <code>.txt</code>, <code>.docx</code> or <code>.pdf</code> and click <b>Detect</b>.</li>
            <li>Check the analytics, then read the document: click a highlight to keep it, select text to add one.</li>
            <li>Pick a mask style and download the redacted file.</li>
          </ol>
        </section>
      )}
    </div>
  );
}
