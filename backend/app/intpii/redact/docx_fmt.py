"""DOCX: edit w:t text in place so run formatting, tables and layout are preserved."""
from __future__ import annotations

import io
import zipfile

from docx import Document
from docx.oxml.ns import qn

from .core import Redactable, normalise, replacement, STYLES

W_T, W_P, W_TAB, W_BR, W_CR = qn("w:t"), qn("w:p"), qn("w:tab"), qn("w:br"), qn("w:cr")
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
MAX_UNCOMPRESSED = 200 * 1024 * 1024
MAILTO = ("mailto:", "tel:")


def _pieces(p) -> list[tuple[object, str, bool]]:
    """Text pieces of one paragraph, excluding paragraphs nested in text boxes."""
    out = []
    for el in p.iter(W_T, W_TAB, W_BR, W_CR):
        anc = el.getparent()
        while anc is not None and anc.tag != W_P:
            anc = anc.getparent()
        if anc is not p:
            continue
        if el.tag == W_T:
            out.append((el, el.text or "", True))
        elif el.tag == W_TAB:
            out.append((el, "\t", False))
        elif el.tag == W_BR and el.get(qn("w:type")) in (None, "textWrapping"):
            out.append((el, "\n", False))
        elif el.tag == W_CR:
            out.append((el, "\n", False))
    return out


def _paragraphs(doc) -> list:
    roots = [doc.element.body]
    for sec in doc.sections:
        for part in (sec.header, sec.first_page_header, sec.even_page_header,
                     sec.footer, sec.first_page_footer, sec.even_page_footer):
            if not part.is_linked_to_previous:
                roots.append(part._element)
    seen, paras = set(), []
    for r in roots:
        for p in r.iter(W_P):
            if id(p) not in seen:
                seen.add(id(p))
                paras.append(p)
    return paras


def _open(data: bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_UNCOMPRESSED:
                raise ValueError("DOCX expands to more than 200 MB; refusing to open it")
        return Document(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("not a valid .docx file")


class DocxDoc(Redactable):
    def __init__(self, data: bytes):
        doc = _open(data)
        paras = _paragraphs(doc)
        units = ["".join(t for _, t, _ in _pieces(p)) for p in paras]
        warnings = []
        names = [str(p.partname) for p in doc.part.package.iter_parts()]
        for needle in ("comments", "footnotes", "endnotes"):
            if any(needle in n for n in names):
                warnings.append(f"This file has {needle}, which are NOT scanned and are left unchanged.")
        if any("/media/" in n for n in names):
            warnings.append("This file has embedded images; text inside images is NOT detected or redacted.")
        if doc.element.xpath("//w:del | //w:ins"):
            warnings.append("This file has tracked changes; deleted text may still be stored in the file.")
        super().__init__("docx", units, "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                         ".docx", data, warnings)

    def render(self, spans, style):
        if style not in STYLES:
            raise ValueError(f"style must be one of {STYLES}")
        doc = _open(self.data)
        paras = _paragraphs(doc)
        if len(paras) != len(self.units):
            raise RuntimeError("document changed between analysis and export")
        for idx, p in enumerate(paras):
            sp = normalise(spans.get(idx, []))
            if not sp:
                continue
            pieces = _pieces(p)
            text = "".join(t for _, t, _ in pieces)
            if text != self.units[idx]:
                raise RuntimeError("document changed between analysis and export")
            starts, pos = [], 0
            for _, t, _ in pieces:
                starts.append(pos)
                pos += len(t)
            new = [t for _, t, _ in pieces]
            for label, s, e in reversed(sp):
                repl, first = replacement(label, text[s:e], style), True
                for i, (_, t, editable) in enumerate(pieces):
                    a, b = max(s, starts[i]) - starts[i], min(e, starts[i] + len(t)) - starts[i]
                    if not editable or b <= a:
                        continue
                    new[i] = new[i][:a] + (repl if first else "") + new[i][b:]
                    first = False
            for (el, old, editable), t in zip(pieces, new):
                if editable and t != old:
                    el.text = t
                    el.set(XML_SPACE, "preserve")
        self._scrub(doc)
        out = io.BytesIO()
        doc.save(out)
        return out.getvalue()

    @staticmethod
    def _scrub(doc) -> None:
        cp = doc.core_properties
        for attr in ("author", "last_modified_by", "title", "subject", "keywords", "comments", "category"):
            setattr(cp, attr, "")
        for part in doc.part.package.iter_parts():
            for rel in part.rels.values():
                if rel.is_external and rel.target_ref.lower().startswith(MAILTO):
                    rel._target = rel.target_ref.split(":", 1)[0] + ":redacted"
