"""PDF: true redaction by flattening. Each page is rendered to an image with black boxes burned in,
so the covered text no longer exists anywhere in the output (it is not selectable or searchable)."""
from __future__ import annotations

import io

import pypdfium2 as pdfium

from .core import Redactable, normalise

MAX_PAGES = 30
DPI = 150
PAD = 1.5  # points


def _open(data: bytes):
    try:
        return pdfium.PdfDocument(data)
    except pdfium.PdfiumError as e:
        raise ValueError(f"could not open PDF (encrypted or damaged?): {e}")


def _page_text(page, number: int) -> str:
    if page.get_rotation() != 0:
        raise ValueError(f"page {number} is rotated; rotated pages are not supported")
    tp = page.get_textpage()
    try:
        n = tp.count_chars()
        text = tp.get_text_range(0, n) if n else ""
    finally:
        tp.close()
    if len(text) != n:
        # Fail closed: offsets would not line up with character boxes.
        raise ValueError(f"page {number} has a text layout that cannot be mapped safely")
    return text


def _line_boxes(tp, text: str, s: int, e: int) -> list[list[float]]:
    boxes: list[list[float]] = []
    cur = None
    for i in range(s, e):
        if text[i] in "\r\n":
            cur = None
            continue
        l, b, r, t = tp.get_charbox(i, loose=True)
        if r <= l or t <= b:
            continue
        h = t - b
        if cur and min(t, cur[3]) - max(b, cur[1]) > 0.5 * h and l - cur[2] < 3 * h:
            cur[0], cur[1] = min(cur[0], l), min(cur[1], b)
            cur[2], cur[3] = max(cur[2], r), max(cur[3], t)
        else:
            cur = [l, b, r, t]
            boxes.append(cur)
    return boxes


class PdfDoc(Redactable):
    def __init__(self, data: bytes):
        pdf = _open(data)
        try:
            if len(pdf) > MAX_PAGES:
                raise ValueError(f"PDF has {len(pdf)} pages; the limit is {MAX_PAGES}")
            units, warnings, empty = [], [], []
            for i in range(len(pdf)):
                page = pdf[i]
                try:
                    units.append(_page_text(page, i + 1))
                finally:
                    page.close()
                if not units[-1].strip():
                    empty.append(i + 1)
        finally:
            pdf.close()
        if empty:
            warnings.append(
                f"Page(s) {', '.join(map(str, empty))} have no text layer (scanned image?). "
                "Nothing can be detected there and they are copied unredacted. OCR is not supported yet.")
        warnings.append("Output is flattened to images: redacted text is truly removed, but the whole "
                        "document becomes non-selectable and non-searchable.")
        super().__init__("pdf", units, "application/pdf", ".pdf", data, warnings)

    def render(self, spans, style):
        from PIL import ImageDraw

        pdf = _open(self.data)
        images = []
        try:
            for i in range(len(pdf)):
                page = pdf[i]
                try:
                    text = _page_text(page, i + 1)
                    if text != self.units[i]:
                        raise RuntimeError("document changed between analysis and export")
                    scale = DPI / 72
                    img = page.render(scale=scale).to_pil().convert("RGB")
                    cl, cb, cr, ct = page.get_cropbox()
                    draw = ImageDraw.Draw(img)
                    tp = page.get_textpage()
                    try:
                        for _, s, e in normalise(spans.get(i, [])):
                            for l, b, r, t in _line_boxes(tp, text, s, e):
                                draw.rectangle([(l - cl - PAD) * scale, (ct - t - PAD) * scale,
                                                (r - cl + PAD) * scale, (ct - b + PAD) * scale], fill="black")
                    finally:
                        tp.close()
                    images.append(img)
                finally:
                    page.close()
        finally:
            pdf.close()
        out = io.BytesIO()
        images[0].save(out, "PDF", save_all=True, append_images=images[1:], resolution=DPI, quality=90)
        return out.getvalue()
