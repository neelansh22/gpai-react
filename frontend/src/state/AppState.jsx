import { createContext, useCallback, useContext, useState } from "react";
import { endpoints } from "../api/client";

const AppStateContext = createContext(null);

const initialStatus = {
  provider: "Local (offline)",
  has_key: false,
  processed: false,
  trained: false,
  has_clusters: false,
  rows: 0,
};

export function AppStateProvider({ children }) {
  const [status, setStatus] = useState(initialStatus);
  const [dataPreview, setDataPreview] = useState(null);
  const [processInfo, setProcessInfo] = useState(null);
  const [clusterData, setClusterData] = useState(null);
  const [modelMetrics, setModelMetrics] = useState(null);
  const [diagnosis, setDiagnosis] = useState(null);
  const [history, setHistory] = useState([]);
  const [toast, setToast] = useState(null);

  const notify = useCallback((message, tone = "info") => {
    setToast({ message, tone, id: Date.now() });
    window.clearTimeout(notify._t);
    notify._t = window.setTimeout(() => setToast(null), 3500);
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const { data } = await endpoints.getConfig();
      setStatus(data);
      return data;
    } catch (e) {
      return null;
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const { data } = await endpoints.history();
      setHistory(data.history || []);
    } catch (e) {
      /* ignore */
    }
  }, []);

  const value = {
    status,
    setStatus,
    refreshStatus,
    dataPreview,
    setDataPreview,
    processInfo,
    setProcessInfo,
    clusterData,
    setClusterData,
    modelMetrics,
    setModelMetrics,
    diagnosis,
    setDiagnosis,
    history,
    setHistory,
    refreshHistory,
    toast,
    notify,
  };

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used inside AppStateProvider");
  return ctx;
}
