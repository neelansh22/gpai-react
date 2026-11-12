// Shared PII entity-highlighting helpers (colors + text overlay), ported from int-pii/ui/src/ui.tsx.
export const LABELS = ["PERSON", "AGE", "ADDRESS", "EMAIL", "PHONE"];

export const COLORS = {
  PERSON: "#a78bfa",
  AGE: "#fbbf24",
  ADDRESS: "#34d399",
  EMAIL: "#60a5fa",
  PHONE: "#fb7185",
};

/** Render `text` with non-overlapping `entities` (label/start/end/score) highlighted. */
export function Highlight({ text, entities }) {
  const sorted = [...entities].sort((a, b) => a.start - b.start || b.end - a.end);
  const parts = [];
  let pos = 0;
  sorted.forEach((e, i) => {
    if (e.start < pos) return;
    if (e.start > pos) parts.push(text.slice(pos, e.start));
    parts.push(
      <mark
        key={i}
        className="rounded px-0.5"
        style={{ background: `${COLORS[e.label]}33`, borderBottom: `2px solid ${COLORS[e.label]}` }}
        title={`${e.label}${e.score !== undefined ? ` (${e.score.toFixed(2)})` : ""}`}
      >
        {text.slice(e.start, e.end)}
        <sup className="ml-0.5 font-semibold" style={{ color: COLORS[e.label] }}>
          {e.label}
        </sup>
      </mark>
    );
    pos = e.end;
  });
  parts.push(text.slice(pos));
  return <div className="whitespace-pre-wrap break-words font-mono text-sm leading-relaxed text-slate-200">{parts}</div>;
}

export function Legend() {
  return (
    <div className="mb-3 flex flex-wrap gap-3 text-xs text-slate-400">
      {Object.entries(COLORS).map(([label, color]) => (
        <span key={label} className="inline-flex items-center gap-1.5">
          <i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: color }} />
          {label}
        </span>
      ))}
    </div>
  );
}
