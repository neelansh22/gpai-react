import { useEffect, useState } from "react";
import { errorMessage } from "../api/monitorClient";
import { useMonitorState } from "../state/MonitorState";

/** Loads data from a monitor endpoint, reloading on range change or manual refresh. */
export function useMonitorData(fetcher) {
  const { range, refreshTick } = useMonitorState();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher(range)
      .then((res) => !cancelled && setData(res.data))
      .catch((e) => !cancelled && setError(errorMessage(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range, refreshTick]);

  return { data, error, loading };
}
