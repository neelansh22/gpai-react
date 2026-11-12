"""Span-level metrics: exact match and overlap match, per label."""
from __future__ import annotations

from collections import defaultdict

from ..types import LABELS, Span


def _match(gold: list[tuple[int, int]], pred: list[tuple[int, int]], exact: bool) -> int:
    used: set[int] = set()
    tp = 0
    for gs, ge in gold:
        for i, (ps, pe) in enumerate(pred):
            if i in used:
                continue
            ok = (gs, ge) == (ps, pe) if exact else (gs < pe and ps < ge)
            if ok:
                used.add(i)
                tp += 1
                break
    return tp


def score(docs, predictions: list[list[Span]]) -> dict:
    """Returns {label: {mode: {tp, fp, fn, precision, recall, f1}}} plus an ALL entry."""
    counts = {lab: {"exact": [0, 0, 0], "overlap": [0, 0, 0]} for lab in (*LABELS, "ALL")}
    for doc, preds in zip(docs, predictions):
        for lab in LABELS:
            g = [(s, e) for l, s, e in doc.gold if l == lab]
            p = [(s.start, s.end) for s in preds if s.label == lab]
            for mode in ("exact", "overlap"):
                tp = _match(g, p, mode == "exact")
                for key in (lab, "ALL"):
                    c = counts[key][mode]
                    c[0] += tp
                    c[1] += len(p) - tp
                    c[2] += len(g) - tp
    out = defaultdict(dict)
    for lab, modes in counts.items():
        for mode, (tp, fp, fn) in modes.items():
            pr = tp / (tp + fp) if tp + fp else 0.0
            rc = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
            out[lab][mode] = {"tp": tp, "fp": fp, "fn": fn, "precision": pr, "recall": rc, "f1": f1}
    return dict(out)


def errors(docs, predictions: list[list[Span]], context: int = 40) -> list[dict]:
    """Per-span overlap-mode misses (fn) and false alarms (fp) with surrounding text."""
    out = []
    for di, (doc, preds) in enumerate(zip(docs, predictions)):
        used: set[int] = set()
        for lab, gs, ge in doc.gold:
            hit = None
            for i, p in enumerate(preds):
                if i not in used and p.label == lab and gs < p.end and p.start < ge:
                    hit = i
                    break
            if hit is None:
                out.append({"doc": di, "type": "fn", "label": lab, "start": gs, "end": ge,
                            "text": doc.text[gs:ge], "context": _ctx(doc.text, gs, ge, context)})
            else:
                used.add(hit)
        for i, p in enumerate(preds):
            if i not in used:
                out.append({"doc": di, "type": "fp", "label": p.label, "start": p.start,
                            "end": p.end, "text": p.text, "score": p.score,
                            "context": _ctx(doc.text, p.start, p.end, context)})
    return out


def _ctx(text: str, s: int, e: int, n: int) -> dict:
    return {"before": text[max(0, s - n):s], "span": text[s:e], "after": text[e:e + n]}
