"""Combine detectors. Recall first: keep the union, but dedupe same-label overlaps."""
from __future__ import annotations

from .types import Span

# Validated structured types: the rule-based span wins over the model span.
RULE_PRIORITY = {"EMAIL", "PHONE", "AGE"}


def merge(rule_spans: list[Span], model_spans: list[Span]) -> list[Span]:
    out: list[Span] = list(rule_spans)
    for m in model_spans:
        clash = [r for r in rule_spans if r.label == m.label and r.overlaps(m)]
        if clash and m.label in RULE_PRIORITY:
            continue
        out.append(m)
    # Same-label overlaps from different sources: keep the longer (more complete) span.
    out.sort(key=lambda s: (s.label, s.start, -(s.end - s.start)))
    kept: list[Span] = []
    for s in out:
        if kept and kept[-1].label == s.label and kept[-1].overlaps(s):
            continue
        kept.append(s)
    return sorted(kept, key=lambda s: (s.start, s.end))
