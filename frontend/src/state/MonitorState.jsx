import { createContext, useContext, useState } from "react";

const MonitorContext = createContext(null);

export function MonitorStateProvider({ children }) {
  const [range, setRange] = useState("7d");
  const [refreshTick, setRefreshTick] = useState(0);
  const refresh = () => setRefreshTick((t) => t + 1);

  return (
    <MonitorContext.Provider value={{ range, setRange, refreshTick, refresh }}>
      {children}
    </MonitorContext.Provider>
  );
}

export function useMonitorState() {
  const ctx = useContext(MonitorContext);
  if (!ctx) throw new Error("useMonitorState must be used within MonitorStateProvider");
  return ctx;
}
