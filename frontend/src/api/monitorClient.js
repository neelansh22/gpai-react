import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const KEY_STORAGE = "skyline_monitor_key";

export const monitorApi = axios.create({ baseURL: API_BASE, timeout: 60000 });

monitorApi.interceptors.request.use((config) => {
  const key = localStorage.getItem(KEY_STORAGE);
  if (key) config.headers["X-Monitor-Key"] = key;
  return config;
});

export const monitorKey = {
  get: () => localStorage.getItem(KEY_STORAGE) || "",
  set: (v) => (v ? localStorage.setItem(KEY_STORAGE, v) : localStorage.removeItem(KEY_STORAGE)),
};

export const monitorEndpoints = {
  status: () => monitorApi.get("/api/monitor/status"),
  usage: (range) => monitorApi.get("/api/monitor/usage", { params: { range } }),
  cache: (range) => monitorApi.get("/api/monitor/cache", { params: { range } }),
  heatmap: () => monitorApi.get("/api/monitor/heatmap"),
};

export function errorMessage(err) {
  return err?.response?.data?.detail || err?.message || "Request failed";
}

export default monitorApi;
