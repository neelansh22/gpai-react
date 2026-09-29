import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8010";

export const pricingApi = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
});

function buildParams(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, values]) => {
    if (!values) return;
    (Array.isArray(values) ? values : [values]).forEach((v) => params.append(key, v));
  });
  return params;
}

export const pricingEndpoints = {
  filters: () => pricingApi.get("/api/pricing/filters"),
  kpis: (filters) => pricingApi.get(`/api/pricing/kpis?${buildParams(filters)}`),
  scatter: (filters) => pricingApi.get(`/api/pricing/scatter?${buildParams(filters)}`),
  table: (filters) => pricingApi.get(`/api/pricing/table?${buildParams(filters)}`),
  trend: (filters) => pricingApi.get(`/api/pricing/trend?${buildParams(filters)}`),
  yearlyBar: (filters) => pricingApi.get(`/api/pricing/yearly-bar?${buildParams(filters)}`),
  classPie: (filters) => pricingApi.get(`/api/pricing/class-pie?${buildParams(filters)}`),
};

export default pricingApi;
