import type { AddedSpan, Entity, RedactAnalysis, RedactStyle, Dataset, EvalResult, Health, Mode, Run, SweepPoint, Trace } from "./types";

const API_BASE = import.meta.env.VITE_PII_API_URL || (import.meta.env.DEV ? "http://localhost:8001" : "");
function url(path: string): string {
  if (!API_BASE) throw new Error("VITE_PII_API_URL is not configured for the hosted PII service");
  return `${API_BASE.replace(/\/$/, "")}/api/pii${path}`;
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const endpoint = url(path);
  try {
    return await fetch(endpoint, init);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("Cannot reach the PII service. It may be starting or temporarily unavailable, or the browser may be blocking the connection. Please retry.", { cause: error });
    }
    throw error;
  }
}

function utf16Offsets(text: string): number[] {
  const offsets = [0];
  for (const char of text) offsets.push(offsets[offsets.length - 1] + char.length);
  return offsets;
}

function convertEntities<T extends Entity>(entities: T[], offsets: number[]): T[] {
  return entities.map((e) => ({ ...e, start: offsets[e.start], end: offsets[e.end] }));
}

const documents = new Map<string, Map<number, string>>();

async function job<T>(kind: "eval" | "sweep", payload: Record<string, unknown>): Promise<T> {
  const { job_id } = await call<{ job_id: string }>("/jobs", { kind, ...payload });
  while (true) {
    const status = await call<{ status: string; error?: string; result?: T }>(`/jobs/${encodeURIComponent(job_id)}`);
    if (status.status === "failed") throw new Error(status.error || "Evaluation failed");
    if (status.status === "completed") {
      if (status.result === undefined) throw new Error("Evaluation completed without a result");
      return status.result;
    }
    if (status.status !== "queued" && status.status !== "running") throw new Error(`Unknown evaluation status: ${status.status}`);
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}

async function call<T>(path: string, body?: unknown): Promise<T> {
  const r = await request(path, body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch { /* keep */ }
    throw new Error(`${r.status}: ${msg}`);
  }
  return r.json() as Promise<T>;
}

export const modelSize = {
  get: () => "small",
  set: (s: string) => localStorage.setItem("intpii.size", s),
};

async function fail(r: Response): Promise<never> {
  let msg = r.statusText;
  try { const j = await r.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch { /* keep */ }
  throw new Error(`${r.status}: ${msg}`);
}

export const redact = {
  analyze: async (file: File, mode: Mode, threshold: number): Promise<RedactAnalysis> => {
    const q = new URLSearchParams({ filename: file.name, mode, threshold: String(threshold), size: modelSize.get() });
    const r = await request(`/redact/analyze?${q}`, { method: "POST", body: file });
    if (!r.ok) return fail(r);
    const result: RedactAnalysis = await r.json();
    const units = new Map(result.units.map((unit) => [unit.id, unit.text]));
    documents.set(result.doc_id, units);
    result.spans = result.spans.map((span) => {
      const text = units.get(span.unit);
      if (text === undefined) throw new Error("Server returned a span for an unknown document unit");
      return convertEntities([span], utf16Offsets(text))[0];
    });
    return result;
  },
  exportFile: async (docId: string, style: RedactStyle, rejected: string[], added: AddedSpan[]): Promise<{ blob: Blob; name: string }> => {
    const units = documents.get(docId);
    if (!units) throw new Error("Document session is unavailable; analyze the file again");
    const serverSpans = added.map((span) => {
      const text = units.get(span.unit);
      if (text === undefined) throw new Error("Manual redaction references an unknown document unit");
      return { ...span, start: Array.from(text.slice(0, span.start)).length, end: Array.from(text.slice(0, span.end)).length };
    });
    const r = await request("/redact/export", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: docId, style, rejected, added: serverSpans }),
    });
    if (!r.ok) return fail(r);
    const m = /filename="([^"]+)"/.exec(r.headers.get("content-disposition") ?? "");
    return { blob: await r.blob(), name: m ? m[1] : "redacted" };
  },
  discard: async (docId: string) => {
    const response = await request(`/redact/${docId}`, { method: "DELETE" });
    if (!response.ok) return fail(response);
    documents.delete(docId);
  },
};

export const api = {
  health: () => call<Health>("/health"),
  datasets: () => call<Dataset[]>("/datasets"),
  runs: () => call<Run[]>("/runs"),
  extract: async (text: string, mode: Mode, threshold: number) => {
    const trace = await call<Trace>("/extract", { text, mode, threshold, size: modelSize.get() });
    const offsets = utf16Offsets(text);
    trace.entities = convertEntities(trace.entities, offsets);
    trace.chunks = trace.chunks.map((c) => ({ ...c, start: offsets[c.start], end: offsets[c.end],
      regex: convertEntities(c.regex, offsets), model: convertEntities(c.model, offsets), merged: convertEntities(c.merged, offsets) }));
    return trace;
  },
  evaluate: async (dataset: string, mode: Mode, threshold: number, n: number) => {
    const result = await job<EvalResult>("eval", { dataset, mode, threshold, n, size: modelSize.get() });
    result.documents = result.documents.map((d) => {
      const offsets = utf16Offsets(d.text);
      return { ...d, gold: convertEntities(d.gold, offsets), pred: convertEntities(d.pred, offsets) };
    });
    return result;
  },
  sweep: (dataset: string, mode: Mode, n: number) =>
    job<{ points: SweepPoint[]; approximation: boolean }>("sweep", { dataset, mode, n, size: modelSize.get() }),
};
