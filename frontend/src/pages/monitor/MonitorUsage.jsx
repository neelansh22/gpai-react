import { useMemo } from "react";
import { BarChart3 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { PageHeader, Spinner } from "../../components/ui";
import { monitorEndpoints } from "../../api/monitorClient";
import { useMonitorData } from "../../state/useMonitorData";
import { ChartCard, Empty, ErrorCard, TOOL_COLORS } from "./shared";

const tipStyle = { background: "#0f172a", border: "1px solid #334155", borderRadius: 8 };

export default function MonitorUsage() {
  const { data, error, loading } = useMonitorData(monitorEndpoints.usage);

  const { rows, toolNames } = useMemo(() => {
    const byBucket = {};
    const names = new Set();
    (data?.series || []).forEach((s) => {
      const key = String(s.bucket).slice(0, data.range === "24h" ? 16 : 10);
      byBucket[key] = byBucket[key] || { bucket: key };
      byBucket[key][s.tool] = s.calls;
      names.add(s.tool);
    });
    return { rows: Object.values(byBucket), toolNames: [...names] };
  }, [data]);

  return (
    <div>
      <PageHeader
        icon={BarChart3}
        title="API Usage"
        subtitle="Which tools the voice agent calls, and how they perform"
        accent="amber"
        tip="Each row is a Function endpoint the agent can call. High p95 latency or failures here are what a caller would hear as pauses or apologies."
      />

      {error && <ErrorCard message={error} />}

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-8 w-8 text-amber-400" />
        </div>
      ) : (
        data && (
          <div className="space-y-6">
            <ChartCard title="Calls over time" tip="Call volume per tool across the selected range, bucketed hourly for 24h and daily otherwise.">
              {rows.length ? (
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={rows}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="bucket" stroke="#64748b" fontSize={11} />
                      <YAxis stroke="#64748b" allowDecimals={false} />
                      <RTooltip contentStyle={tipStyle} />
                      <Legend />
                      {toolNames.map((n, i) => (
                        <Bar key={n} dataKey={n} stackId="a" fill={TOOL_COLORS[i % TOOL_COLORS.length]} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <Empty />
              )}
            </ChartCard>

            <ChartCard title="Per-tool performance" tip="p50 is the typical response time, p95 the slow tail. Failures counts non-successful responses.">
              {data.tools.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs uppercase tracking-wider text-slate-500">
                      <tr>
                        <th className="py-2">Tool</th>
                        <th>Calls</th>
                        <th>p50 (ms)</th>
                        <th>p95 (ms)</th>
                        <th>Failures</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.tools.map((t) => (
                        <tr key={t.tool} className="border-t border-slate-800/70 text-slate-300">
                          <td className="py-2 font-medium text-white">{t.tool}</td>
                          <td>{t.calls}</td>
                          <td>{Math.round(t.p50)}</td>
                          <td>{Math.round(t.p95)}</td>
                          <td className={t.failures ? "text-rose-300" : ""}>{t.failures}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty />
              )}
            </ChartCard>

            <ChartCard title="Agent activity" tip="What the Foundry agent itself did: tool invocations, realtime model turns, and speech in and out.">
              {data.agent.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs uppercase tracking-wider text-slate-500">
                      <tr>
                        <th className="py-2">Kind</th>
                        <th>Name</th>
                        <th>Calls</th>
                        <th>Avg (ms)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.agent.map((a) => (
                        <tr key={`${a.kind}-${a.name}`} className="border-t border-slate-800/70 text-slate-300">
                          <td className="py-2">{a.kind}</td>
                          <td className="font-medium text-white">{a.name}</td>
                          <td>{a.calls}</td>
                          <td>{Math.round(a.avg_ms)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty />
              )}
            </ChartCard>
          </div>
        )
      )}
    </div>
  );
}
