"""
int-pii: local PII detection & redaction (regex + GLiNER-ONNX hybrid).

Ported from the standalone int-pii FastAPI app into this backend as a router
so it shares the same process/CORS config as the other demos. Only the
"small" GLiNER ONNX model is bundled (backend/models/gliner-pii-small) to
keep the deploy footprint small; it is loaded lazily on first request.
"""
from __future__ import annotations

import re
import logging
import secrets
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .intpii.redact import MAX_BYTES, STYLES, find_spans, open_document
from .intpii.models.gliner_onnx import SHA256
from .intpii.service import Engine, MODES
from .intpii.types import LABELS, Span

router = APIRouter(prefix="/api/pii", tags=["pii"])

SIZES = ("small",)  # only the "small" GLiNER model is bundled in this deploy

_engine = Engine(load_model=False)
_engine_lock = threading.Lock()
logger = logging.getLogger(__name__)


def get_engine(mode: str = "hybrid") -> Engine:
    if mode != "regex" and not _engine.model_loaded:
        with _engine_lock:
            if not _engine.model_loaded:
                try:
                    _engine.load("small")
                except (RuntimeError, OSError, ValueError) as exc:
                    logger.exception("Could not load the PII model")
                    raise HTTPException(503, "PII model could not be loaded") from exc
    return _engine


class ExtractReq(BaseModel):
    text: str = Field(max_length=200_000)
    mode: str = "hybrid"
    size: str = "small"
    threshold: float = Field(0.3, ge=0.01, le=0.99)

class EvalReq(BaseModel):
    dataset: str
    mode: str = "hybrid"
    size: str = "small"
    threshold: float = Field(0.3, ge=0.01, le=0.99)
    n: int = Field(300, ge=1, le=2000)
    seed: int = 0

class SweepReq(BaseModel):
    dataset: str
    mode: str = "hybrid"
    size: str = "small"
    thresholds: list[float] = Field(default_factory=lambda: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], max_length=100)
    n: int = Field(300, ge=1, le=2000)
    seed: int = 0


def _check(mode: str, size: str = "small") -> Engine:
    if mode not in MODES:
        raise HTTPException(400, f"mode must be one of {MODES}")
    if size not in SIZES:
        raise HTTPException(400, f"size must be one of {SIZES}")
    engine = get_engine(mode)
    if mode != "regex" and not engine.model_loaded:
        raise HTTPException(503, "model not loaded")
    return engine


@router.get("/health")
def pii_health():
    import onnxruntime

    return {"ok": True, "model_loaded": _engine.model_loaded, "modes": MODES,
            "sizes": _engine.available_sizes(), "loaded_sizes": _engine.loaded_sizes(),
            "labels": LABELS, "onnxruntime": onnxruntime.__version__,
            "model_sha256": SHA256["model_quint8.onnx"], "recall_target": 0.95,
            "latency_target_s": 1.0}


@router.post("/extract")
def pii_extract(req: ExtractReq):
    engine = _check(req.mode, req.size)
    return engine.extract_trace(req.text, req.mode, req.threshold, size="small")


_runs: list[dict] = []
_runs_lock = threading.Lock()


@router.get("/datasets")
def datasets():
    return [{"name": "synthetic (template generator)", "id": "synthetic"}]


def evaluate(req: EvalReq):
    if req.dataset != "synthetic":
        raise HTTPException(400, "Only the synthetic dataset is available on the hosted demo")
    engine = _check(req.mode, req.size)
    result = engine.evaluate(req.dataset, req.mode, req.threshold, req.n, req.seed, req.size)
    all_metrics = result["metrics"]["ALL"]["overlap"]
    run = {"file": f"synthetic-n{req.n}-seed{req.seed}-{req.mode}-t{req.threshold}",
           "recall": all_metrics["recall"], "precision": all_metrics["precision"],
           "f1": all_metrics["f1"], "p50_s": result["latency"]["p50_s"],
           "p95_s": result["latency"]["p95_s"]}
    with _runs_lock:
        _runs.append(run)
        del _runs[:-50]
    return result


def sweep(req: SweepReq):
    if req.dataset != "synthetic":
        raise HTTPException(400, "Only the synthetic dataset is available on the hosted demo")
    if not req.thresholds or any(not 0.01 <= t <= 0.99 for t in req.thresholds):
        raise HTTPException(400, "thresholds must be between 0.01 and 0.99")
    engine = _check(req.mode, req.size)
    return engine.sweep(req.dataset, req.mode, sorted(set(req.thresholds)), req.n, req.seed, req.size)


@router.get("/runs")
def runs():
    with _runs_lock:
        return list(_runs)


class JobReq(BaseModel):
    kind: str
    dataset: str
    mode: str = "hybrid"
    size: str = "small"
    threshold: float = Field(0.3, ge=0.01, le=0.99)
    thresholds: list[float] = Field(default_factory=lambda: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], max_length=100)
    n: int = Field(300, ge=1, le=2000)
    seed: int = 0


_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_job_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pii-evaluation")
JOB_TTL = 30 * 60


def _run_job(job_id: str, req: JobReq) -> None:
    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
    try:
        if req.kind == "eval":
            result = evaluate(EvalReq(**req.model_dump()))
        else:
            result = sweep(SweepReq(**req.model_dump()))
    except Exception:
        logger.exception("PII evaluation job failed")
        with _jobs_lock:
            _jobs[job_id].update(status="failed", error="Evaluation failed; check service logs", finished=time.time())
    else:
        with _jobs_lock:
            _jobs[job_id].update(status="completed", result=result, finished=time.time())


@router.post("/jobs", status_code=202)
def create_job(req: JobReq):
    if req.kind not in ("eval", "sweep"):
        raise HTTPException(400, "kind must be eval or sweep")
    if req.dataset != "synthetic" or req.mode not in MODES or req.size not in SIZES:
        raise HTTPException(400, "unsupported dataset, mode or model size")
    if req.kind == "sweep" and (not req.thresholds or any(not 0.01 <= t <= 0.99 for t in req.thresholds)):
        raise HTTPException(400, "thresholds must be between 0.01 and 0.99")
    with _jobs_lock:
        if any(job["status"] in ("queued", "running") for job in _jobs.values()):
            raise HTTPException(429, "An evaluation is already running; try again when it completes")
        completed = sorted(
            (key for key, job in _jobs.items() if "finished" in job),
            key=lambda key: _jobs[key]["finished"],
        )
        for key in completed[:-2]:
            del _jobs[key]
        job_id = secrets.token_urlsafe(18)
        _jobs[job_id] = {"status": "queued"}
        _job_executor.submit(_run_job, job_id, req)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Evaluation job expired or is unknown")
        return dict(job)


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


def purge_expired_sessions() -> None:
    with _sessions_lock:
        now = time.time()
        for key in [key for key, value in _sessions.items() if now - value["t"] > SESSION_TTL]:
            del _sessions[key]
    with _jobs_lock:
        now = time.time()
        for key in [key for key, value in _jobs.items() if "finished" in value and now - value["finished"] > JOB_TTL]:
            del _jobs[key]


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
async def redact_analyze(request: Request, filename: str, mode: str = "hybrid", size: str = "small", threshold: float = 0.3):
    if not 0.01 <= threshold <= 0.99:
        raise HTTPException(400, "threshold must be between 0.01 and 0.99")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BYTES:
        raise HTTPException(413, "file too large")
    chunks = []
    length = 0
    async for chunk in request.stream():
        length += len(chunk)
        if length > MAX_BYTES:
            raise HTTPException(413, "file too large")
        chunks.append(chunk)
    data = b"".join(chunks)
    engine = await run_in_threadpool(_check, mode, size)

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
        _purge()
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
    stem = re.sub(r"[^a-zA-Z0-9_.-]+", "_", Path(sess["filename"]).stem)[:80] or "document"
    return Response(out, media_type=doc.mime, headers={
        "Content-Disposition": f'attachment; filename="{stem}.redacted{doc.ext}"', "Cache-Control": "no-store"})


@router.delete("/redact/{doc_id}")
def redact_delete(doc_id: str):
    with _sessions_lock:
        _sessions.pop(doc_id, None)
    return {"deleted": True}
