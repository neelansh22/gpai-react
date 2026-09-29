import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

export const endpoints = {
  health: () => api.get("/api/health"),
  configure: (payload) => api.post("/api/configure", payload),
  getConfig: () => api.get("/api/config"),
  loadUrl: (url) => api.post("/api/data/load-url", { url }),
  loadFile: (file) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/api/data/load-file", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  preview: () => api.get("/api/data/preview"),
  process: () => api.post("/api/process"),
  cluster: () => api.post("/api/cluster"),
  train: () => api.post("/api/train"),
  diagnose: (symptoms) => api.post("/api/diagnose", { symptoms }),
  history: () => api.get("/api/history"),
  clearHistory: () => api.delete("/api/history"),
  historyAnalysis: () => api.get("/api/history/analysis"),
  getThresholds: () => api.get("/api/thresholds"),
  setThresholds: (payload) => api.put("/api/thresholds", payload),
  reset: () => api.post("/api/reset"),
};

export default api;
