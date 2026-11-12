"""Deterministic baseline recognisers. Free-form names and addresses mostly need a model."""
from __future__ import annotations

import re

from ..types import Span

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_PHONE = re.compile(
    r"(?<![\w.])(?:\+\d{1,3}[ -]?)?"
    r"(?:(?:\(\d{2,4}\)[ -]?|\d{2,4}[ -])\d{3,4}[ -]\d{3,4}|\d{5}[ -]\d{5,6})(?!\w)"
)

_UNITS = "one|two|three|four|five|six|seven|eight|nine"
_TEENS = "ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen"
_TENS = "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
_WORDNUM = rf"(?:(?:{_TENS})(?:[- ](?:{_UNITS}))?|{_TEENS}|{_UNITS})"
_NUM = rf"(?:\d{{1,3}}|{_WORDNUM})"
_SEP = r"(?:\s*-\s*|\s+)"
_AGE_PATTERNS = [
    # "aged 34", "age: forty-one"
    re.compile(rf"\b(?:aged?\s*:?)\s*(?P<n>{_NUM})\b", re.IGNORECASE),
    # "34 years old", "a 29-year-old", "seventy-eight years old"
    re.compile(rf"\b(?P<n>{_NUM}){_SEP}years?{_SEP}old\b", re.IGNORECASE),
    # form field incl. common OCR typos: "Age: 45", "Ag3: 58", "Aqe: 45" (digits only; avoids prose)
    re.compile(r"\b[Aa][gq][e3]\s*[:=]\s*(?P<n>\d{1,3})\b"),
]

_TITLE = r"(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Nurse|Sir|Madam)"
# Title + optional initials + one capitalised word, e.g. "Mr Verma", "Mrs T. Fairweather", "Dr. A. B. Smith".
_TITLED_NAME = re.compile(rf"\b{_TITLE}\.?\s+(?:[A-Z]\.\s*)*[A-Z][A-Za-z'’-]+")

# UK postcodes, and US ZIPs only when preceded by a state code (bare 5-digit numbers are too ambiguous).
_POSTCODE = re.compile(r"\b(?:[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}|[A-Z]{2}\s+\d{5}(?:-\d{4})?)\b")


def detect_regex(text: str) -> list[Span]:
    spans: list[Span] = []
    for m in _EMAIL.finditer(text):
        spans.append(Span("EMAIL", m.start(), m.end(), m.group()))
    for m in _PHONE.finditer(text):
        spans.append(Span("PHONE", m.start(), m.end(), m.group()))
    seen: set[tuple[int, int]] = set()
    for pat in _AGE_PATTERNS:
        for m in pat.finditer(text):
            if m.span("n") not in seen:
                seen.add(m.span("n"))
                spans.append(Span("AGE", m.start("n"), m.end("n"), m.group("n")))
    for m in _TITLED_NAME.finditer(text):
        spans.append(Span("PERSON", m.start(), m.end(), m.group()))
    for m in _POSTCODE.finditer(text):
        spans.append(Span("ADDRESS", m.start(), m.end(), m.group()))
    return sorted(spans, key=lambda s: (s.start, s.end))
