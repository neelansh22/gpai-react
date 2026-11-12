"""Chunk -> detect -> remap offsets -> merge, producing one JSON record per input."""
from __future__ import annotations

from typing import Iterable, Iterator

from .detectors import Detector
from .ingest.chunk import iter_chunks
from .types import Span, validate_spans


def _dedupe(spans: list[Span]) -> list[Span]:
    # Overlapping chunks see the same entity twice, sometimes cut short: keep the longest.
    spans = sorted(spans, key=lambda s: (s.label, s.start, -(s.end - s.start)))
    kept: list[Span] = []
    for s in spans:
        if kept and kept[-1].label == s.label and kept[-1].overlaps(s):
            if s.end - s.start > kept[-1].end - kept[-1].start:
                kept[-1] = s
            continue
        kept.append(s)
    return sorted(kept, key=lambda s: (s.start, s.end))


def extract(text: str, detect: Detector, max_chars: int = 1200, overlap: int = 200) -> list[Span]:
    found: list[Span] = []
    for base, chunk in iter_chunks(text, max_chars, overlap):
        for s in detect(chunk):
            found.append(Span(s.label, s.start + base, s.end + base, s.text, s.score))
    spans = _dedupe(found)
    validate_spans(text, spans)
    return spans


def run(records: Iterable[tuple[str, str]], detect: Detector, include_text: bool = True,
        max_chars: int = 1200, overlap: int = 200) -> Iterator[dict]:
    for rec_id, text in records:
        spans = extract(text, detect, max_chars, overlap)
        yield {
            "id": rec_id,
            "chars": len(text),
            "entities": [
                {"label": s.label, "start": s.start, "end": s.end, "score": round(s.score, 3),
                 **({"text": s.text} if include_text else {})}
                for s in spans
            ],
        }
