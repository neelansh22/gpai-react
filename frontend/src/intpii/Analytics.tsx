import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { COLORS, LABELS, type Label } from "./types";

export type AItem = { label: Label; text: string; score?: number };
export type Focus = { label?: Label; text?: string } | null;
export type Stage = { name: string; counts: Partial<Record<Label, number>> };

export const keyOf = (t: string) => t.trim().toLowerCase();
export const matchesFocus = (f: Focus, label: Label, text: string) =>
  !f || ((!f.label || f.label === label) && (!f.text || keyOf(f.text) === keyOf(text)));

type Pt = { x: number; y: number; label: Label; text: string; count: number; avg: number | null };

// Clusters sit on a ring; entities inside a cluster follow a sunflower spiral so they never overlap exactly.
const RING = 14;
const centre = (i: number) => {
  const a = -Math.PI / 2 + (i * 2 * Math.PI) / LABELS.length;
  return { cx: RING * Math.cos(a), cy: RING * Math.sin(a) };
};

function buildPoints(items: AItem[]): Record<Label, Pt[]> {
  const groups = new Map<string, { label: Label; text: string; n: number; sum: number; scored: number }>();
  for (const it of items) {
    const k = `${it.label}|${keyOf(it.text)}`;
    const g = groups.get(k) ?? { label: it.label, text: it.text.trim(), n: 0, sum: 0, scored: 0 };
    g.n += 1;
    if (it.score !== undefined) { g.sum += it.score; g.scored += 1; }
    groups.set(k, g);
  }
  const out = { PERSON: [], AGE: [], ADDRESS: [], EMAIL: [], PHONE: [] } as Record<Label, Pt[]>;
  LABELS.forEach((label, li) => {
    const g = [...groups.values()].filter((x) => x.label === label).sort((a, b) => b.n - a.n || a.text.localeCompare(b.text));
    const step = Math.min(2.2, 7 / Math.sqrt(Math.max(g.length, 1)));
    const { cx, cy } = centre(li);
    g.forEach((x, k) => {
      const r = step * Math.sqrt(k + 0.5), a = k * 2.399963;
      out[label].push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a), label, text: x.text, count: x.n,
        avg: x.scored ? x.sum / x.scored : null });
    });
  });
  return out;
}

type View = "treemap" | "3d";
const rgba = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`;
};
const safe = (s: string) => s.replace(/[<>&]/g, "").slice(0, 60);
const TOP = 150;

function EntityPlot({ points, focus, view, pick, pickLabel }: {
  points: Record<Label, Pt[]>; focus: Focus; view: View; pick: (p: Pt) => void; pickLabel: (l: Label) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const cb = useRef({ pick, pickLabel });
  const [chartError, setChartError] = useState("");
  useEffect(() => { cb.current = { pick, pickLabel }; }, [pick, pickLabel]);

  useEffect(() => {
    const el = ref.current as (HTMLDivElement & { on: (e: string, f: (d: never) => unknown) => void; removeAllListeners?: (e: string) => void }) | null;
    if (!el) return;
    let live = true;
    import("plotly.js/dist/plotly.min.js").then(({ default: Plotly }) => {
      if (!live) return;
      Plotly.purge(el);
      const font = { color: "#e6e8f2", size: 11 };
      const hoverlabel = { bgcolor: "#1b1d2a", bordercolor: "#2c2f44", font: { color: "#e6e8f2" } };
      const cfg = { displaylogo: false, displayModeBar: false, responsive: true };
      if (view === "treemap") {
        const ids: string[] = [], labels: string[] = [], parents: string[] = [], values: number[] = [], colors: string[] = [], text: string[] = [];
        LABELS.forEach((l) => {
          const pts = points[l];
          if (!pts.length) return;
          ids.push(l); labels.push(l); parents.push(""); values.push(0); colors.push(rgba(COLORS[l], 0.9));
          text.push(`${l}: ${pts.reduce((n, x) => n + x.count, 0)} spans, ${pts.length} distinct`);
          pts.slice(0, TOP).forEach((x) => {
            ids.push(`${l}|${keyOf(x.text)}`); labels.push(safe(x.text)); parents.push(l); values.push(x.count);
            colors.push(rgba(COLORS[l], matchesFocus(focus, x.label, x.text) ? 0.6 : 0.12));
            text.push(`${l}: ${safe(x.text)}<br>seen ${x.count}\u00d7${x.avg !== null ? ` \u00b7 avg score ${x.avg.toFixed(2)}` : ""}`);
          });
          const rest = pts.slice(TOP);
          if (rest.length) {
            ids.push(`${l}|__other`); labels.push(`+${rest.length} more`); parents.push(l);
            values.push(rest.reduce((n, x) => n + x.count, 0)); colors.push(rgba(COLORS[l], 0.25)); text.push(`${rest.length} more distinct ${l} values`);
          }
        });
        Plotly.react(el, [{ type: "treemap", ids, labels, parents, values, text, hovertemplate: "%{text}<extra></extra>", textinfo: "label+value",
          branchvalues: "remainder", marker: { colors, line: { color: "#0f1019", width: 1 } }, pathbar: { visible: false }, tiling: { pad: 2 }, textfont: font }],
          { height: 340, margin: { l: 0, r: 0, t: 0, b: 0 }, paper_bgcolor: "rgba(0,0,0,0)", hoverlabel }, cfg);
        el.removeAllListeners?.("plotly_treemapclick");
        el.on("plotly_treemapclick", ((d: { points: { id: string }[] }) => {
          const id = d.points[0]?.id ?? "";
          const [l, k] = id.split("|");
          const pt = points[l as Label]?.find((x) => keyOf(x.text) === k);
          if (pt) cb.current.pick(pt); else if (!k) cb.current.pickLabel(l as Label);
          return false;
        }) as never);
      } else {
        const axis = { backgroundcolor: "rgba(0,0,0,0)", gridcolor: "#2c2f44", zerolinecolor: "#2c2f44", color: "#9aa0b8" };
        const traces = LABELS.map((l, li) => ({
          type: "scatter3d", mode: "markers", name: l, customdata: points[l],
          x: points[l].map((_, k) => li + ((k * 0.618) % 1 - 0.5) * 0.5),
          y: points[l].map((p) => p.avg ?? 1), z: points[l].map((p) => p.count),
          marker: { size: points[l].map((p) => Math.min(4 + 2 * Math.sqrt(p.count), 16)),
            color: points[l].map((p) => rgba(COLORS[l], matchesFocus(focus, p.label, p.text) ? 0.9 : 0.1)), line: { width: 0 } },
          hovertemplate: points[l].map((p) => `<b>${p.label}</b><br>${safe(p.text)}<br>seen ${p.count}\u00d7 \u00b7 score ${(p.avg ?? 1).toFixed(2)}<extra></extra>`),
        }));
        Plotly.react(el, traces, {
          height: 340, margin: { l: 0, r: 0, t: 0, b: 0 }, paper_bgcolor: "rgba(0,0,0,0)", hoverlabel,
          legend: { orientation: "h", y: 0, font: { color: "#9aa0b8", size: 11 } },
          scene: {
            camera: { eye: { x: 1.6, y: -1.6, z: 0.9 } },
            xaxis: { ...axis, title: "", tickvals: LABELS.map((_, i) => i), ticktext: LABELS, range: [-0.6, LABELS.length - 0.4] },
            yaxis: { ...axis, title: "avg confidence", range: [0, 1.05] },
            zaxis: { ...axis, title: "times seen", rangemode: "tozero" },
          },
        }, cfg);
        el.removeAllListeners?.("plotly_click");
        el.on("plotly_click", ((d: { points: { customdata?: Pt }[] }) => { const p = d.points[0]?.customdata; if (p) cb.current.pick(p); }) as never);
      }
    }).catch((error) => { if (live) setChartError(`Chart could not be loaded: ${String(error)}`); });
    return () => { live = false; };
  }, [points, focus, view]);

  useEffect(() => () => {
    const el = ref.current;
    if (el) import("plotly.js/dist/plotly.min.js").then(({ default: Plotly }) => Plotly.purge(el));
  }, []);

  return <>{chartError && <div className="error">{chartError}</div>}<div ref={ref} style={{ width: "100%", height: 340 }} /></>;
}

export function Analytics({ items, chars, ms, stages, focus, onFocus }: {
  items: AItem[]; chars: number; ms?: number; stages?: Stage[]; focus: Focus; onFocus: (f: Focus) => void;
}) {
  const points = useMemo(() => buildPoints(items), [items]);
  const [view, setView] = useState<View>("treemap");
  const counts = useMemo(() => {
    const c = {} as Record<Label, number>;
    LABELS.forEach((l) => { c[l] = items.filter((i) => i.label === l).length; });
    return c;
  }, [items]);
  const scored = items.filter((i) => i.score !== undefined) as (AItem & { score: number })[];
  const unique = new Set(items.map((i) => `${i.label}|${keyOf(i.text)}`)).size;
  const avg = scored.length ? scored.reduce((a, b) => a + b.score, 0) / scored.length : null;
  const low = scored.filter((i) => i.score < 0.5).length;

  const hist = useMemo(() => Array.from({ length: 10 }, (_, b) => {
    const row: Record<string, number | string> = { bin: (b / 10).toFixed(1) };
    LABELS.forEach((l) => { row[l] = scored.filter((s) => s.label === l && Math.min(Math.floor(s.score * 10), 9) === b).length; });
    return row;
  }), [scored]);

  const stageRows = useMemo(() => LABELS.map((l) => {
    const row: Record<string, number | string> = { label: l };
    stages?.forEach((s) => { row[s.name] = s.counts[l] ?? 0; });
    return row;
  }), [stages]);

  const kpis: [string, string][] = [
    ["Entities", String(items.length)], ["Unique", String(unique)],
    ["Per 1k chars", chars ? ((items.length / chars) * 1000).toFixed(1) : "0"],
    ["Avg score", avg === null ? "–" : avg.toFixed(2)],
    ["Low confidence", scored.length ? `${low} (<0.5)` : "–"],
    ...(ms !== undefined ? [["Latency", `${Math.round(ms)} ms`] as [string, string]] : []),
  ];

  const toggleLabel = (l: Label) => onFocus(focus?.label === l && !focus.text ? null : { label: l });
  const pick = (p: Pt) => onFocus(focus?.label === p.label && focus.text && keyOf(focus.text) === keyOf(p.text) ? null : { label: p.label, text: p.text });

  return (
    <div className="analytics">
      <div className="mkpis">{kpis.map(([k, v]) => <div key={k} className="mk"><span>{k}</span><b>{v}</b></div>)}</div>

      <div className="chips">
        {LABELS.map((l) => (
          <button key={l} className={`chip ${focus?.label === l ? "on" : ""}`} style={{ borderColor: COLORS[l] }}
            onClick={() => toggleLabel(l)} disabled={!counts[l]}>
            <i style={{ background: COLORS[l] }} />{l} <b>{counts[l]}</b>
          </button>))}
        {focus && (
          <button className="chip clear" onClick={() => onFocus(null)}>
            Focus: {focus.label}{focus.text ? ` · ${focus.text.slice(0, 24)}` : ""} ✕
          </button>)}
      </div>

      <h3>Entity clusters
        <span className="seg">
          <button className={view === "treemap" ? "on" : ""} onClick={() => setView("treemap")}>Treemap</button>
          <button className={view === "3d" ? "on" : ""} onClick={() => setView("3d")}>3D</button>
        </span>
        <small className="muted">{view === "treemap" ? "area = how often it appears \u00b7 click a tile to focus" : "drag to rotate \u00b7 height = times seen \u00b7 depth = confidence"}</small></h3>
      <div className="chart" style={{ height: 340 }}>
        {items.length === 0 ? <p className="muted pad">No entities found.</p> : (
          <EntityPlot points={points} focus={focus} view={view} pick={pick} pickLabel={toggleLabel} />)}
      </div>

      {scored.length > 0 && (
        <>
          <h3>Confidence <small className="muted">number of entities per score band</small></h3>
          <div className="chart" style={{ height: 170 }}>
            <ResponsiveContainer>
              <BarChart data={hist} margin={{ top: 4, right: 10, bottom: 0, left: -14 }}>
                <CartesianGrid stroke="#2c2f44" vertical={false} />
                <XAxis dataKey="bin" stroke="#9aa0b8" fontSize={11} />
                <YAxis stroke="#9aa0b8" fontSize={11} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#1b1d2a", border: "1px solid #2c2f44" }} cursor={{ fill: "#ffffff10" }} />
                {LABELS.map((l) => <Bar key={l} dataKey={l} stackId="s" fill={COLORS[l]} isAnimationActive={false} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>)}

      {stages && stages.length > 0 && (
        <>
          <h3>Who found what <small className="muted">spans per stage and entity type</small></h3>
          <div className="chart" style={{ height: 190 }}>
            <ResponsiveContainer>
              <BarChart data={stageRows} margin={{ top: 4, right: 10, bottom: 0, left: -14 }}>
                <CartesianGrid stroke="#2c2f44" vertical={false} />
                <XAxis dataKey="label" stroke="#9aa0b8" fontSize={11} />
                <YAxis stroke="#9aa0b8" fontSize={11} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#1b1d2a", border: "1px solid #2c2f44" }} cursor={{ fill: "#ffffff10" }} />
                {stages.map((s, i) => <Bar key={s.name} dataKey={s.name} fill={["#64748b", "#a78bfa", "#34d399"][i % 3]}
                  radius={[3, 3, 0, 0]} isAnimationActive={false} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="legend">{stages.map((s, i) => (
            <span key={s.name}><i style={{ background: ["#64748b", "#a78bfa", "#34d399"][i % 3] }} />{s.name}</span>))}</div>
        </>)}
    </div>
  );
}
