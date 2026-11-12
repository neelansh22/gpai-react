"""GLiNER PII tagger run from a local, pinned ONNX file (no pickle loading)."""
from __future__ import annotations

from pathlib import Path

from ..types import Span

MODELS_ROOT = Path(__file__).resolve().parents[3] / "models"
MODEL_DIR = MODELS_ROOT / "gliner-pii-small"
LABEL_MAP = {
    "person name": "PERSON",
    "age": "AGE",
    "street address": "ADDRESS",
    "email address": "EMAIL",
    "phone number": "PHONE",
}
SHA256 = {
    "model_quint8.onnx": "891589426ee96f2748b16439f44fad8c3f97e198e002a6637e58dee989500216",
    "model.onnx": "c60fd671a30798c1bfad5828f8bbf6214eb44cbc5e2f0fb968563ae935a17454",
}


# size -> (directory, {onnx file: sha256}); revisions are noted in the README.
_BASE_SHA = {"model_quint8.onnx": "0514c8fd86d0513ce5351a3267f132b57d5bcd8f99a90d43cde1228092881d19"}
_LARGE_SHA = {"model_quint8.onnx": "65260f808caecc0a9f3ebf3c07303809155a82cd78b20ca5ea1fa06377436c44"}
VARIANTS = {
    "small": ("gliner-pii-small", SHA256),
    "base": ("gliner-pii-base", _BASE_SHA),
    "large": ("gliner-pii-large", _LARGE_SHA),
}


def _verify(path: Path, expected: dict[str, str]) -> None:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    if h.hexdigest() != expected[path.name]:
        raise RuntimeError(f"checksum mismatch for {path.name}")


class GlinerDetector:
    def __init__(self, onnx_file: str = "model_quint8.onnx", threshold: float = 0.3,
                 size: str = "small"):
        from gliner import GLiNER

        dirname, hashes = VARIANTS[size]
        model_dir = MODELS_ROOT / dirname
        _verify(model_dir / "onnx" / onnx_file, hashes)
        self.model = GLiNER.from_pretrained(
            str(model_dir), load_onnx_model=True, onnx_model_file=f"onnx/{onnx_file}",
            load_tokenizer=True,
        )
        self.threshold = threshold

    def __call__(self, text: str) -> list[Span]:
        ents = self.model.predict_entities(text, list(LABEL_MAP), threshold=self.threshold)
        spans = [Span(LABEL_MAP[e["label"]], e["start"], e["end"], text[e["start"]:e["end"]],
                      float(e["score"])) for e in ents]
        return sorted(spans, key=lambda s: (s.start, s.end))
