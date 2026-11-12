from __future__ import annotations

from dataclasses import dataclass

LABELS = ("PERSON", "AGE", "ADDRESS", "EMAIL", "PHONE")


@dataclass(frozen=True)
class Span:
    label: str
    start: int
    end: int
    text: str
    score: float = 1.0

    def overlaps(self, other: "Span") -> bool:
        return self.start < other.end and other.start < self.end


def validate_spans(text: str, spans: list[Span]) -> None:
    """Every span must be copied verbatim from the source (no invented text)."""
    for s in spans:
        if s.label not in LABELS:
            raise ValueError(f"unknown label {s.label!r}")
        if not (0 <= s.start < s.end <= len(text)):
            raise ValueError(f"span out of range: {s}")
        if text[s.start:s.end] != s.text:
            raise ValueError(f"span text is not a substring at its offsets: {s}")
