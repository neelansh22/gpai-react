import { COLORS, type Entity } from "./types";

// Renders text with coloured entity highlights. Overlapping spans: the earlier one wins.
export function Highlight({ text, entities, dim }: { text: string; entities: Entity[]; dim?: boolean }) {
  const sorted = [...entities].sort((a, b) => a.start - b.start || b.end - a.end);
  const parts: React.ReactNode[] = [];
  let pos = 0;
  sorted.forEach((e, i) => {
    if (e.start < pos) return;
    if (e.start > pos) parts.push(text.slice(pos, e.start));
    parts.push(
      <mark key={i} style={{ background: COLORS[e.label] + (dim ? "33" : "44"), borderBottom: `2px solid ${COLORS[e.label]}` }}
        title={`${e.label}${e.score !== undefined ? ` (${e.score.toFixed(2)})` : ""}`}>
        {text.slice(e.start, e.end)}<sup style={{ color: COLORS[e.label] }}>{e.label}</sup>
      </mark>,
    );
    pos = e.end;
  });
  parts.push(text.slice(pos));
  return <div className="doc">{parts}</div>;
}

export function Legend() {
  return (
    <div className="legend">
      {Object.entries(COLORS).map(([k, c]) => <span key={k}><i style={{ background: c }} />{k}</span>)}
    </div>
  );
}

export const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
