"""Parse LLM-written tagged text: [[LABEL|text]] -> plain text + exact gold spans."""
from __future__ import annotations

import re
from pathlib import Path

from .synth import Doc

LABELS = ("PERSON", "AGE", "ADDRESS", "EMAIL", "PHONE")
_TAG = re.compile(r"\[\[([^\[\]|]*)\|([^\[\]|]*)\]\]")
_SEP = re.compile(r"^\s*={5,}\s*$")


class TagError(ValueError):
    pass


def parse_doc(raw: str, first_line: int = 1) -> Doc:
    text, gold, pos = "", [], 0
    for m in _TAG.finditer(raw):
        line = first_line + raw.count("\n", 0, m.start())
        label, value = m.group(1).strip(), m.group(2)
        if label not in LABELS:
            raise TagError(f"line {line}: unknown label {label!r}")
        if not value.strip():
            raise TagError(f"line {line}: empty tag")
        if value != value.strip():
            raise TagError(f"line {line}: tag text has leading/trailing space: {value!r}")
        text += raw[pos:m.start()]
        gold.append((label, len(text), len(text) + len(value)))
        text += value
        pos = m.end()
    text += raw[pos:]
    leftover = re.search(r"\[\[|\]\]", _TAG.sub("", raw))
    if leftover:
        line = first_line + _TAG.sub(lambda m: "\n" * m.group().count("\n"), raw)[:leftover.start()].count("\n")
        raise TagError(f"line {line}: unbalanced or malformed tag")
    return Doc(text, gold)


def load_tagged(path: str | Path) -> list[Doc]:
    docs: list[Doc] = []
    buf: list[str] = []
    start = 1

    def flush(next_start: int) -> None:
        nonlocal buf, start
        raw = "\n".join(buf).strip("\n")
        if raw.strip():
            docs.append(parse_doc(raw, start))
        buf, start = [], next_start

    for i, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        if _SEP.match(line):
            flush(i + 1)
        else:
            buf.append(line)
    flush(0)
    if not docs:
        raise TagError("no documents found")
    return docs
