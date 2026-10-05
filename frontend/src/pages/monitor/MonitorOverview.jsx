import { useMemo } from "react";
import { Gauge } from "lucide-react";
import { Card, Metric, PageHeader, Spinner } from "../../components/ui";
import { monitorEndpoints } from "../../api/monitorClient";
import { useMonitorData } from "../../state/useMonitorData";
import { ErrorCard } from "./shared";

export default function MonitorOverview() {
  const usage = useMonitorData(monitorEndpoints.usage);
  const cache = useMonitorData(monitorEndpoints.cache);

  const totals = useMemo(() => {
    const tools = usage.data?.tools || [];
    const calls = tools.reduce((s, t) => s + (t.calls || 0), 0);
    const failures = tools.reduce((s, t) => s + (t.failures || 0), 0);
    const weighted = tools.reduce((s, t) => s + (t.p50 || 0) * (t.calls || 0), 0);
    return { calls, failures, avg: calls ? Math.round(weighted / calls) : 0 };
  }, [usage.data]);

  const agent = usage.data?.agent || [];
  const turns = agent.filter((a) => a.kind === "model turn").reduce((s, a) => s + a.calls, 0);
  const hitRate = cache.data?.io?.hit_rate;

  return (
    <div>
      <PageHeader
        icon={Gauge}
        title="Skyline Monitor"
        subtitle="Health of the voice travel agent backend at a glance"
        accent="amber"
        tip="Headline numbers for the selected time range: Function API calls, how often the cache answered instead of AeroDataBox, typical latency, and failures. Use the sidebar to change the range."
      />

      {(usage.error || cache.error) && <ErrorCard message={usage.error || cache.error} />}

      {usage.loading || cache.loading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-8 w-8 text-amber-400" />
        </div>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Metric label="API calls" value={totals.calls} accent="amber" hint="Function endpoints" />
            <Metric
              label="Cache hit rate"
              value={hitRate == null ? "—" : `${Math.round(hitRate * 100)}%`}
              accent="emerald"
              hint="Approximate"
            />
            <Metric label="Median latency" value={`${totals.avg} ms`} accent="brand" hint="Call-weighted p50" />
            <Metric
              label="Failures"
              value={totals.failures}
              accent={totals.failures ? "rose" : "emerald"}
              hint={`${turns} model turns`}
            />
          </div>

          <Card>
            <p className="mb-3 text-sm font-semibold text-white">Cache state</p>
            <div className="grid grid-cols-3 gap-4 text-center">
              <Metric label="Entries" value={cache.data?.state?.entries ?? 0} />
              <Metric label="Warm" value={cache.data?.state?.warm ?? 0} accent="emerald" />
              <Metric label="Expired" value={cache.data?.state?.expired ?? 0} accent="amber" />
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
