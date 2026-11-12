"""Detector registry shared by the CLI and the eval harness (heavy imports are lazy)."""
from __future__ import annotations

from typing import Callable

from .recognisers import detect_regex
from .types import Span

Detector = Callable[[str], list[Span]]


def _gliner(size: str = "small", threshold: float = 0.3) -> Detector:
    from .models import GlinerDetector

    return GlinerDetector(size=size, threshold=threshold)


def _hybrid(size: str = "small", threshold: float = 0.3) -> Detector:
    from .merge import merge

    model = _gliner(size, threshold)
    return lambda text: merge(detect_regex(text), model(text))


# Factories take (threshold) so the CLI and eval can tune it; regex ignores it.
DETECTORS: dict[str, Callable[..., Detector]] = {
    "regex": lambda threshold=0.3: detect_regex,
    "gliner": lambda threshold=0.3: _gliner("small", threshold),
    "hybrid": lambda threshold=0.3: _hybrid("small", threshold),
    "gliner-base": lambda threshold=0.3: _gliner("base", threshold),
    "hybrid-base": lambda threshold=0.3: _hybrid("base", threshold),
    "gliner-large": lambda threshold=0.3: _gliner("large", threshold),
    "hybrid-large": lambda threshold=0.3: _hybrid("large", threshold),
}
