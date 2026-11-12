"""Upload -> detect -> mask -> export in the original format (.txt/.md/.csv/.json/.log, .docx, .pdf)."""
from __future__ import annotations

from pathlib import PurePath

from .core import MAX_BYTES, STYLES, Redactable, join_units, split_spans

TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".log"}


def open_document(filename: str, data: bytes) -> Redactable:
    if not data:
        raise ValueError("the file is empty")
    if len(data) > MAX_BYTES:
        raise ValueError(f"file is larger than {MAX_BYTES // (1024 * 1024)} MB")
    ext = PurePath(filename).suffix.lower()
    if ext in TEXT_EXTS:
        from .text import TextDoc

        return TextDoc(data, ext)
    if ext == ".docx":
        from .docx_fmt import DocxDoc

        return DocxDoc(data)
    if ext == ".pdf":
        from .pdf_fmt import PdfDoc

        return PdfDoc(data)
    raise ValueError(f"unsupported file type {ext or '(none)'}; use .txt, .docx or .pdf")


def find_spans(doc: Redactable, detect) -> list[tuple[int, str, int, int, float]]:
    """Run `detect(text) -> list[Span]` over the whole document; return per-unit spans."""
    text, starts = join_units(doc.units)
    found = detect(text)
    scores = {(s.label, s.start, s.end): s.score for s in found}
    out = []
    for s in found:
        for i, lab, a, b in split_spans([(s.label, s.start, s.end)], doc.units, starts):
            out.append((i, lab, a, b, scores[(s.label, s.start, s.end)]))
    return out


__all__ = ["open_document", "find_spans", "STYLES", "MAX_BYTES"]
