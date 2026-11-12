"""Format-independent redaction helpers: masking styles, span clean-up, unit mapping."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

STYLES = ("box", "label", "partial")
MAX_BYTES = 20 * 1024 * 1024

# (label, start, end) in the coordinates of one unit (paragraph, page or whole text).
UnitSpan = tuple[str, int, int]


@dataclass
class Redactable:
    kind: str
    units: list[str]
    mime: str
    ext: str
    data: bytes
    warnings: list[str] = field(default_factory=list)

    def render(self, spans: dict[int, list[UnitSpan]], style: str) -> bytes:
        raise NotImplementedError


def normalise(spans: list[UnitSpan]) -> list[UnitSpan]:
    """Sort and merge overlapping spans so each character is masked once."""
    out: list[UnitSpan] = []
    for label, s, e in sorted(spans, key=lambda x: (x[1], x[2])):
        if e <= s:
            continue
        if out and s < out[-1][2]:
            pl, ps, pe = out[-1]
            out[-1] = (pl, ps, max(pe, e))
        else:
            out.append((label, s, e))
    return out


def replacement(label: str, original: str, style: str) -> str:
    if style == "label":
        return f"[{label}]"
    if style == "partial":
        if label == "EMAIL" and "@" in original:
            local, _, domain = original.rpartition("@")
            return local[:1] + "***@" + domain
        if label == "PHONE":
            digits = [i for i, c in enumerate(original) if c.isdigit()]
            keep = set(digits[-2:])
            return "".join(c if (not c.isdigit() or i in keep) else "*" for i, c in enumerate(original))
        if label == "AGE":
            return re.sub(r"\d", "*", original)
        return re.sub(r"(\S)(\S*)", lambda m: m.group(1) + "*" * len(m.group(2)), original)
    return "".join(c if c.isspace() else "\u2588" for c in original)


def apply_text(text: str, spans: list[UnitSpan], style: str) -> str:
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}")
    out, pos = [], 0
    for label, s, e in normalise(spans):
        out.append(text[pos:s])
        out.append(replacement(label, text[s:e], style))
        pos = e
    out.append(text[pos:])
    return "".join(out)


def join_units(units: list[str]) -> tuple[str, list[int]]:
    """One text for detection (so context carries across units) plus each unit's start offset."""
    starts, pos = [], 0
    for u in units:
        starts.append(pos)
        pos += len(u) + 1
    return "\n".join(units), starts


def split_spans(spans: list[tuple[str, int, int]], units: list[str], starts: list[int]):
    """Map spans over the joined text back to (unit index, label, start, end), clipping at unit edges."""
    out = []
    for label, s, e in spans:
        for i, (u, base) in enumerate(zip(units, starts)):
            a, b = max(s, base), min(e, base + len(u))
            if b > a:
                out.append((i, label, a - base, b - base))
    return out
