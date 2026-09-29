import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const sdodApi = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
});

export const sdodEndpoints = {
  status: () => sdodApi.get("/api/sdod/status"),
  submitIntent: (intent) => sdodApi.post("/api/sdod/intent", { intent }),
  submitAnswers: (answers) => sdodApi.post("/api/sdod/answers", { answers }),
  generateSchema: () => sdodApi.post("/api/sdod/schema/generate"),
  getSchema: () => sdodApi.get("/api/sdod/schema"),
  updateSchema: (schema) => sdodApi.put("/api/sdod/schema", schema),
  uploadSchema: (schema) => sdodApi.post("/api/sdod/schema/upload", schema),
  generateData: (rowsPerTable) => sdodApi.post("/api/sdod/generate", { rows_per_table: rowsPerTable }),
  previewTable: (table, limit = 25) => sdodApi.get("/api/sdod/data/preview", { params: { table, limit } }),
  previewConsolidated: (limit = 25) => sdodApi.get("/api/sdod/data/consolidated", { params: { limit } }),
  exportTableUrl: (table) => `${API_BASE}/api/sdod/data/export?table=${encodeURIComponent(table)}`,
  exportConsolidatedUrl: () => `${API_BASE}/api/sdod/data/export-consolidated`,
  augmentSummary: () => sdodApi.get("/api/sdod/augment/summary"),
  applyRule: (rule) => sdodApi.post("/api/sdod/augment/rule", { rule }),
  resetAugmentation: () => sdodApi.post("/api/sdod/augment/reset"),
  reset: () => sdodApi.post("/api/sdod/reset"),
};

export default sdodApi;
