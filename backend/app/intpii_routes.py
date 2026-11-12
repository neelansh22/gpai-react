"""
int-pii: local PII detection & redaction (regex + GLiNER-ONNX hybrid).

Ported from the standalone int-pii FastAPI app into this backend as a router
so it shares the same process/CORS config as the other demos. Only the
"small" GLiNER ONNX model is bundled (backend/models/gliner-pii-small) to
keep the deploy footprint small; it is loaded lazily on first request.
"""
from __future__ import annotations

import re
import secrets
import threading
import time
from collections import OrderedDict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .intpii.redact import MAX_BYTES, STYLES, find_spans, open_document
from .intpii.service import Engine, MODES
from .intpii.types import LABELS, Span

router = APIRouter(prefix="/api/pii", tags=["pii"])

SIZES = ("small",)  # only the "small" GLiNER model is bundled in this deploy

_engine: Engine | None = None
_engine_lock = threading.Lock()


def get_engine() -> Engine:
    """Lazily create and load the GLiNER engine (first call pays the ~seconds-long load cost)."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = Engine(load_model=False)
                _engine.load("small")
    return _engine


class ExtractReq(BaseModel):
    text: str = Field(max_length=200_000)
    mode: str = "hybrid"
    threshold: float = Field(0.3, ge=0.01, le=0.99)


def _check(mode: str) -> Engine:
    if mode not in MODES:
        raise HTTPException(400, f"mode must be one of {MODES}")
    engine = get_engine()
    if mode != "regex" and not engine.model_loaded:
        raise HTTPException(503, "model not loaded")
    return engine


@router.get("/health")
def pii_health():
    import onnxruntime

    engine = get_engine()
    return {"ok": True, "model_loaded": engine.model_loaded, "modes": MODES, "sizes": list(SIZES),
            "labels": LABELS, "onnxruntime": onnxruntime.__version__}


@router.post("/extract")
def pii_extract(req: ExtractReq):
    engine = _check(req.mode)
    return engine.extract_trace(req.text, req.mode, req.threshold, size="small")


# ---- Upload -> detect -> review -> redact -> export -------------------------------------------
# Uploads live only in memory (never written to disk) and expire after SESSION_TTL seconds.
SESSION_TTL, MAX_SESSIONS = 30 * 60, 5
_sessions: "OrderedDict[str, dict]" = OrderedDict()
_sessions_lock = threading.Lock()


def _purge() -> None:
    now = time.time()
    for k in [k for k, v in _sessions.items() if now - v["t"] > SESSION_TTL]:
        del _sessions[k]
    while len(_sessions) > MAX_SESSIONS:
        _sessions.popitem(last=False)


class AddedSpan(BaseModel):
    unit: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    label: str


class ExportReq(BaseModel):
    doc_id: str
    style: str = "box"
    added: list[AddedSpan] = Field(default_factory=list, max_length=10_000)
    rejected: list[str] = Field(default_factory=list, max_length=100_000)


@router.post("/redact/analyze")
async def redact_analyze(request: Request, filename: str, mode: str = "hybrid", threshold: float = 0.3):
    engine = _check(mode)
    if not 0.01 <= threshold <= 0.99:
        raise HTTPException(400, "threshold must be between 0.01 and 0.99")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BYTES:
        raise HTTPException(413, "file too large")
    data = await request.body()

    def work():
        doc = open_document(filename, data)
        t0 = time.perf_counter()

        def detect(text: str):
            tr = engine.extract_trace(text, mode, threshold, size="small")
            return [Span(e["label"], e["start"], e["end"], e["text"], e["score"]) for e in tr["entities"]]

        found = find_spans(doc, detect)
        return doc, found, time.perf_counter() - t0

    try:
        doc, found, secs = await run_in_threadpool(work)
    except ValueError as e:
        raise HTTPException(400, str(e))
    doc_id = secrets.token_urlsafe(12)
    with _sessions_lock:
        _purge()
        spans = [{"id": f"{i}:{a}:{b}:{lab}", "unit": i, "label": lab, "start": a, "end": b,
                  "text": doc.units[i][a:b], "score": round(sc, 3)} for i, lab, a, b, sc in found]
        _sessions[doc_id] = {"doc": doc, "filename": filename, "t": time.time(), "spans": spans}
    return {"doc_id": doc_id, "kind": doc.kind, "filename": filename, "warnings": doc.warnings,
            "units": [{"id": i, "text": u} for i, u in enumerate(doc.units) if u],
            "spans": spans, "ms": round(secs * 1e3, 1), "mode": mode, "size": "small", "threshold": threshold,
            "ttl_s": SESSION_TTL}


@router.post("/redact/export")
async def redact_export(req: ExportReq):
    if req.style not in STYLES:
        raise HTTPException(400, f"style must be one of {STYLES}")
    with _sessions_lock:
        _purge()
        sess = _sessions.get(req.doc_id)
    if sess is None:
        raise HTTPException(404, "session expired or unknown; upload the file again")
    doc, rejected = sess["doc"], set(req.rejected)
    by_unit: dict[int, list] = {}
    for sp in sess["spans"]:
        if sp["id"] not in rejected:
            by_unit.setdefault(sp["unit"], []).append((sp["label"], sp["start"], sp["end"]))
    for a in req.added:
        if a.label not in LABELS or a.unit >= len(doc.units) or not a.start < a.end <= len(doc.units[a.unit]):
            raise HTTPException(400, f"invalid manual redaction: {a.model_dump()}")
        by_unit.setdefault(a.unit, []).append((a.label, a.start, a.end))
    try:
        out = await run_in_threadpool(doc.render, by_unit, req.style)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(400, str(e))
    stem = re.sub(r"[^\w.-]+", "_", Path(sess["filename"]).stem)[:80] or "document"
    return Response(out, media_type=doc.mime, headers={
        "Content-Disposition": f'attachment; filename="{stem}.redacted{doc.ext}"', "Cache-Control": "no-store"})


@router.delete("/redact/{doc_id}")
def redact_delete(doc_id: str):
    with _sessions_lock:
        _sessions.pop(doc_id, None)
    return {"deleted": True}
