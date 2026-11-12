import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const piiApi = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
});

export const piiEndpoints = {
  health: () => piiApi.get("/api/pii/health"),
  extract: (text, mode, threshold) => piiApi.post("/api/pii/extract", { text, mode, threshold }),
  redactAnalyze: (file, mode, threshold) =>
    piiApi.post(`/api/pii/redact/analyze?filename=${encodeURIComponent(file.name)}&mode=${mode}&threshold=${threshold}`, file, {
      headers: { "Content-Type": file.type || "application/octet-stream" },
    }),
  redactExport: (docId, style, added, rejected) =>
    piiApi.post(
      "/api/pii/redact/export",
      { doc_id: docId, style, added, rejected },
      { responseType: "blob" }
    ),
  redactDelete: (docId) => piiApi.delete(`/api/pii/redact/${docId}`),
};

export default piiApi;
