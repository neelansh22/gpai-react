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
            <p className="mt-4 text-xs text-slate-500">{io.note}</p>
          </>
        )
      )}
    </div>
  );
}
