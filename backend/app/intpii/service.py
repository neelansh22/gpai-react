"""Engine used by the API: traced extraction, dataset evaluation and threshold sweeps."""
from __future__ import annotations

import statistics
import threading
import time
from pathlib import Path

from .ingest.chunk import iter_chunks
from .merge import merge
from .pipeline import _dedupe
from .recognisers import detect_regex
from .types import Span, validate_spans

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "eval"
DATA_DIR = EVAL_DIR / "testinputdata"
RESULTS_DIR = EVAL_DIR / "results"
MODES = ("regex", "gliner", "hybrid")
SWEEP_FLOOR = 0.05


def _eval_modules():
    from .evaluation import metrics, synth, tagged
    return metrics, synth, tagged


def span_dict(s: Span) -> dict:
    return {"label": s.label, "start": s.start, "end": s.end, "text": s.text, "score": round(s.score, 3)}


class Engine:
    def __init__(self, load_model: bool = True):
        self._lock = threading.Lock()
        self._models: dict = {}
        self.model_loaded = False
        if load_model:
            self.load("small")

    def available_sizes(self) -> list[str]:
        from .models.gliner_onnx import MODELS_ROOT, VARIANTS

        return [s for s, (d, _) in VARIANTS.items() if (MODELS_ROOT / d / "onnx" / "model_quint8.onnx").is_file()]

    def load(self, size: str = "small") -> None:
        """Load a model size once (verifies its SHA-256); later calls are no-ops."""
        if size in self._models:
            return
        from .models import GlinerDetector

        det = GlinerDetector(size=size)
        det(" warm up")
        self._models[size] = det
        self.model_loaded = True

    def loaded_sizes(self) -> list[str]:
        return list(self._models)

    def _model(self, text: str, threshold: float, size: str = "small") -> list[Span]:
        det = self._models.get(size)
        if det is None:
            raise RuntimeError(f"model {size!r} not loaded")
        det.threshold = threshold
        return det(text)

    def _detect_chunk(self, chunk: str, mode: str, threshold: float, size: str = "small"):
        t0 = time.perf_counter()
        rules = detect_regex(chunk) if mode in ("regex", "hybrid") else []
        t1 = time.perf_counter()
        model = self._model(chunk, threshold, size) if mode in ("gliner", "hybrid") else []
        t2 = time.perf_counter()
        merged = merge(rules, model) if mode == "hybrid" else (rules or model)
        t3 = time.perf_counter()
        return rules, model, merged, (t1 - t0, t2 - t1, t3 - t2)

    def extract_trace(self, text: str, mode: str, threshold: float, max_chars: int = 1200,
                      overlap: int = 200, size: str = "small") -> dict:
        with self._lock:
            chunks, found, tot = [], [], [0.0, 0.0, 0.0]
            for base, chunk in iter_chunks(text, max_chars, overlap):
                rules, model, merged, (tr, tm, tg) = self._detect_chunk(chunk, mode, threshold, size)
                shift = lambda ss: [span_dict(Span(s.label, s.start + base, s.end + base, s.text, s.score))
                                    for s in ss]
                chunks.append({"start": base, "end": base + len(chunk), "regex": shift(rules),
                               "model": shift(model), "merged": shift(merged),
                               "ms": {"regex": round(tr * 1e3, 2), "model": round(tm * 1e3, 2),
                                      "merge": round(tg * 1e3, 2)}})
                found += [Span(s.label, s.start + base, s.end + base, s.text, s.score) for s in merged]
                tot = [tot[0] + tr, tot[1] + tm, tot[2] + tg]
            t = time.perf_counter()
            final = _dedupe(found)
            validate_spans(text, final)
            dd = time.perf_counter() - t
        return {"chars": len(text), "mode": mode, "size": size, "threshold": threshold, "chunks": chunks,
                "entities": [span_dict(s) for s in final],
                "ms": {"regex": round(tot[0] * 1e3, 2), "model": round(tot[1] * 1e3, 2),
                       "merge": round(tot[2] * 1e3, 2), "dedupe": round(dd * 1e3, 2),
                       "total": round((sum(tot) + dd) * 1e3, 2)}}

    def datasets(self) -> list[dict]:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        out = [{"name": "synthetic (template generator)", "id": "synthetic"}]
        for p in sorted(DATA_DIR.glob("*.txt")):
            out.append({"name": p.name, "id": p.name, "bytes": p.stat().st_size})
        return out

    def _load_docs(self, dataset: str, n: int = 300, seed: int = 0):
        _, synth, tagged = _eval_modules()
        if dataset == "synthetic":
            return synth.generate(n, seed)
        path = (DATA_DIR / dataset).resolve()
        if path.parent != DATA_DIR.resolve() or path.suffix != ".txt" or not path.is_file():
            raise ValueError("unknown dataset")
        return tagged.load_tagged(path)

    def evaluate(self, dataset: str, mode: str, threshold: float, n: int = 300, seed: int = 0,
                 size: str = "small") -> dict:
        metrics, _, _ = _eval_modules()
        docs = self._load_docs(dataset, n, seed)
        preds, times = [], []
        with self._lock:
            for d in docs:
                t = time.perf_counter()
                found = []
                for base, chunk in iter_chunks(d.text, 1200, 200):
                    *_, merged, _ = self._detect_chunk(chunk, mode, threshold, size)
                    found += [Span(s.label, s.start + base, s.end + base, s.text, s.score) for s in merged]
                spans = _dedupe(found)
                times.append(time.perf_counter() - t)
                preds.append(spans)
        res = self._package(docs, preds, times)
        res.update({"dataset": dataset, "mode": mode, "size": size, "threshold": threshold})
        return res

    @staticmethod
    def _package(docs, preds, times) -> dict:
        metrics, _, _ = _eval_modules()
        times = sorted(times)
        return {"docs": len(docs),
                "entities_gold": sum(len(d.gold) for d in docs),
                "metrics": metrics.score(docs, preds),
                "latency": {"p50_s": statistics.median(times), "p95_s": times[int(0.95 * (len(times) - 1))]},
                "errors": metrics.errors(docs, preds),
                "documents": [{"text": d.text, "gold": [{"label": l, "start": s, "end": e}
                                                        for l, s, e in d.gold],
                               "pred": [span_dict(p) for p in ps]} for d, ps in zip(docs, preds)]}

    def sweep(self, dataset: str, mode: str, thresholds: list[float], n: int = 300, seed: int = 0,
              size: str = "small") -> dict:
        """One model pass at a low floor, then filter by score per threshold (an approximation:
        GLiNER's own span decoding at a higher threshold can differ slightly)."""
        metrics, _, _ = _eval_modules()
        docs = self._load_docs(dataset, n, seed)
        per_doc = []
        with self._lock:
            for d in docs:
                rules, model = [], []
                for base, chunk in iter_chunks(d.text, 1200, 200):
                    r = detect_regex(chunk) if mode in ("regex", "hybrid") else []
                    m = self._model(chunk, SWEEP_FLOOR, size) if mode in ("gliner", "hybrid") else []
                    sh = lambda ss: [Span(s.label, s.start + base, s.end + base, s.text, s.score) for s in ss]
                    rules += sh(r)
                    model += sh(m)
                per_doc.append((rules, model))
        points = []
        for th in thresholds:
            preds = []
            for rules, model in per_doc:
                kept = [s for s in model if s.score >= th]
                merged = merge(rules, kept) if mode == "hybrid" else (rules or kept)
                preds.append(_dedupe(merged))
            res = metrics.score(docs, preds)
            points.append({"threshold": th, "overall": res["ALL"], "labels": {k: v["overlap"] for k, v in res.items()}})
        return {"dataset": dataset, "mode": mode, "size": size, "points": points, "approximation": True}
