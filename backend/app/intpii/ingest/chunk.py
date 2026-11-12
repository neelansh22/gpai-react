"""Overlapping character chunks that keep global offsets."""
from __future__ import annotations

from typing import Iterator


def iter_chunks(text: str, max_chars: int = 1200, overlap: int = 200) -> Iterator[tuple[int, str]]:
    """Yield (global_start, chunk). Cuts prefer whitespace so tokens are not split."""
    if max_chars <= overlap or overlap < 0:
        raise ValueError("need 0 <= overlap < max_chars")
    n = len(text)
    start = 0
    while True:
        end = min(start + max_chars, n)
        if end < n:
            cut = text.rfind(" ", start + max_chars - overlap, end)
            cut = max(cut, text.rfind("\n", start + max_chars - overlap, end))
            if cut > start:
                end = cut
        yield start, text[start:end]
        if end >= n:
            return
        nxt = end - overlap
        if nxt > start:
            ws = text.find(" ", nxt, end)
            nxt = ws + 1 if ws != -1 else nxt
        start = max(nxt, start + 1)
