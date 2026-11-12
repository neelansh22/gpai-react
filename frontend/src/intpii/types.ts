export type Label = "PERSON" | "AGE" | "ADDRESS" | "EMAIL" | "PHONE";
export const LABELS: Label[] = ["PERSON", "AGE", "ADDRESS", "EMAIL", "PHONE"];
export const COLORS: Record<Label, string> = {
  PERSON: "#7c5cff", AGE: "#f59e0b", ADDRESS: "#10b981", EMAIL: "#3b82f6", PHONE: "#ef4444",
};
export type RedactSpan = { id: string; unit: number; label: Label; start: number; end: number; text: string; score: number };
export type RedactAnalysis = {
  doc_id: string; kind: string; filename: string; warnings: string[]; units: { id: number; text: string }[];
  spans: RedactSpan[]; ms: number; ttl_s: number;
};
export type AddedSpan = { unit: number; start: number; end: number; label: Label };
export type RedactStyle = "box" | "label" | "partial";

export type Mode = "regex" | "gliner" | "hybrid";

export interface Entity { label: Label; start: number; end: number; text?: string; score?: number }
export interface Chunk {
  start: number; end: number; regex: Entity[]; model: Entity[]; merged: Entity[];
  ms: { regex: number; model: number; merge: number };
}
export interface Trace {
  chars: number; mode: Mode; threshold: number; chunks: Chunk[]; entities: Entity[];
  ms: { regex: number; model: number; merge: number; dedupe: number; total: number };
}
export interface Counts { tp: number; fp: number; fn: number; precision: number; recall: number; f1: number }
export interface LabelMetrics { exact: Counts; overlap: Counts }
export interface ErrorItem {
  doc: number; type: "fn" | "fp"; label: Label; start: number; end: number; text: string; score?: number;
  context: { before: string; span: string; after: string };
}
export interface EvalResult {
  dataset: string; mode: Mode; threshold: number; docs: number; entities_gold: number;
  metrics: Record<string, LabelMetrics>; latency: { p50_s: number; p95_s: number };
  errors: ErrorItem[];
  documents: { text: string; gold: Entity[]; pred: Entity[] }[];
}
export interface SweepPoint { threshold: number; overall: { overlap: Counts; exact: Counts } }
export interface Health {
  ok: boolean; model_loaded: boolean; sizes: string[]; loaded_sizes: string[]; modes: Mode[]; onnxruntime: string; model_sha256: string;
  recall_target: number; latency_target_s: number;
}
export interface Run { file: string; recall: number; precision: number; f1: number; p50_s: number; p95_s: number }
export interface Dataset { name: string; id: string; bytes?: number }
