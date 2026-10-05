import { DatabaseZap } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip as RTooltip } from "recharts";
import { Metric, PageHeader, Spinner } from "../../components/ui";
import { monitorEndpoints } from "../../api/monitorClient";
import { useMonitorData } from "../../state/useMonitorData";
import { ChartCard, Empty, ErrorCard } from "./shared";

export default function MonitorCache() {
  const { data, error, loading } = useMonitorData(monitorEndpoints.cache);
  const io = data?.io;
  const state = data?.state;

  const ioData = io
    ? [
        { name: "Hits", value: io.hits, color: "#34d399" },
        { name: "Misses", value: io.misses, color: "#fb7185" },
      ].filter((d) => d.value > 0)
    : [];
  const typeData = Object.entries(state?.by_type || {}).map(([name, value]) => ({ name, value }));

  return (
    <div>
      <PageHeader
        icon={DatabaseZap}
        title="Cache"
        subtitle="Is the cache answering requests, or is every search hitting AeroDataBox?"
        accent="amber"
        tip="Every cache hit saves AeroDataBox API units against your 400 a month free quota. A healthy cache means repeat questions on warm routes cost nothing."
      />

      {error && <ErrorCard message={error} />}

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-8 w-8 text-amber-400" />
        </div>
      ) : (
        data && (
          <>
            <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
              <Metric label="Hit rate" value={io.hit_rate == null ? "—" : `${Math.round(io.hit_rate * 100)}%`} accent="emerald" />
              <Metric label="Hits" value={io.hits} accent="emerald" />
              <Metric label="Misses" value={io.misses} accent="rose" />
              <Metric label="Writes" value={io.writes} accent="amber" hint="New entries stored" />
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <ChartCard
                title="Hits vs misses"
                tip="A miss means the data had to come from AeroDataBox and was then stored. This is inferred from Table Storage response codes, so treat it as an estimate."
              >
                {ioData.length ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={ioData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={3}>
                          {ioData.map((d) => (
                            <Cell key={d.name} fill={d.color} />
                          ))}
                        </Pie>
                        <RTooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <Empty />
                )}
              </ChartCard>

              <ChartCard
                title="Cache contents"
                tip="What is stored right now, by lookup type. Warm entries are still valid; expired ones will be refreshed on the next request."
              >
                <div className="mb-4 grid grid-cols-3 gap-3">
                  <Metric label="Entries" value={state.entries} />
                  <Metric label="Warm" value={state.warm} accent="emerald" />
                  <Metric label="Expired" value={state.expired} accent="amber" />
                </div>
                {typeData.length ? (
                  <ul className="space-y-1.5 text-sm">
                    {typeData.map((t) => (
                      <li key={t.name} className="flex justify-between rounded-lg bg-slate-900/60 px-3 py-2">
                        <span className="text-slate-300">{t.name}</span>
                        <span className="font-semibold text-amber-300">{t.value}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Empty text="The cache table is empty." />
                )}
              </ChartCard>
            </div>
            <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
              <ChartCard title="Estimated savings" tip="Each hit avoids one AeroDataBox call. Units per call vary by endpoint, so this counts calls, not billed units.">
                <div className="text-3xl font-bold text-emerald-300">{io.hits}</div>
                <p className="mt-1 text-sm text-slate-400">AeroDataBox calls avoided in this period.</p>
                <p className="mt-3 text-sm text-slate-400">
                  {io.misses + io.hits > 0
                    ? `${io.hits} of ${io.hits + io.misses} lookups were served from cache.`
                    : "No cache lookups recorded in this period."}
                </p>
              </ChartCard>
              <ChartCard title="Storage footprint" tip="Size of the cached JSON payloads currently stored in the ApiCache table.">
                <div className="text-3xl font-bold text-amber-300">{((state.total_bytes || 0) / 1024).toFixed(1)} KB</div>
                <p className="mt-1 text-sm text-slate-400">across {state.entries} entries</p>
              </ChartCard>
              <ChartCard title="How to read this" tip="Definitions for the numbers on this page.">
                <ul className="space-y-1.5 text-xs text-slate-400">
                  <li><b className="text-emerald-300">Hit</b>: answer found in the table (200).</li>
                  <li><b className="text-rose-300">Miss</b>: not found (404), so AeroDataBox was called.</li>
                  <li><b className="text-amber-300">Write</b>: result stored for next time (204).</li>
                  <li><b className="text-slate-200">Warm</b>: entry not yet past its expiry.</li>
                </ul>
              </ChartCard>
            </div>

            <div className="mt-6">
              <ChartCard title="Most recent entries" tip="Latest cached lookups with their age and time until expiry.">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-slate-500">
                      <tr><th className="py-2">Key</th><th>Type</th><th>Stored</th><th>Expires in</th><th>Size</th><th>State</th></tr>
                    </thead>
                    <tbody>
                      {(state.items || []).map((e) => (
                        <tr key={e.key} className="border-t border-slate-800 text-slate-300">
                          <td className="max-w-[320px] truncate py-1.5 font-mono">{e.key}</td>
                          <td>{e.type}</td>
                          <td>{e.stored ? new Date(e.stored).toLocaleString() : "—"}</td>
                          <td>{e.expires_in_min == null ? "—" : e.expires_in_min > 0 ? `${e.expires_in_min} min` : "expired"}</td>
                          <td>{e.size_bytes} B</td>
                          <td className={e.warm ? "text-emerald-300" : "text-amber-300"}>{e.warm ? "warm" : "expired"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </ChartCard>
            </div>
            <p className="mt-4 text-xs text-slate-500">{io.note}</p>
          </>
        )
      )}
    </div>
  );
}
