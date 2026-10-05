import { useMemo } from "react";
import { Globe2 } from "lucide-react";
import Plot from "react-plotly.js";
import { PageHeader, Spinner } from "../../components/ui";
import { monitorEndpoints } from "../../api/monitorClient";
import { useMonitorData } from "../../state/useMonitorData";
import { ChartCard, Empty, ErrorCard } from "./shared";

function RankList({ items, color }) {
  const max = Math.max(1, ...items.map((i) => i.count));
  return (
    <ul className="space-y-2">
      {items.slice(0, 10).map((i) => (
        <li key={i.airport} className="text-sm">
          <div className="mb-1 flex justify-between text-slate-300">
            <span className="font-medium text-white">{i.airport}</span>
            <span>{i.count}</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-800">
            <div className="h-1.5 rounded-full" style={{ width: `${(i.count / max) * 100}%`, background: color }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function MonitorHeatmap() {
  const { data, error, loading } = useMonitorData(() => monitorEndpoints.heatmap());

  const traces = useMemo(() => {
    if (!data) return [];
    const mk = (items, name, color) => {
      const pts = items.filter((i) => i.lat != null);
      return {
        type: "scattergeo",
        mode: "markers",
        name,
        lat: pts.map((p) => p.lat),
        lon: pts.map((p) => p.lon),
        text: pts.map((p) => `${p.airport}: ${p.count}`),
        hoverinfo: "text",
        marker: { size: pts.map((p) => 10 + p.count * 6), color, opacity: 0.65, line: { width: 0 } },
      };
    };
    return [mk(data.origins, "Departures", "#fbbf24"), mk(data.destinations, "Destinations", "#38bdf8")];
  }, [data]);

  const empty = data && !data.origins.length && !data.destinations.length;

  return (
    <div>
      <PageHeader
        icon={Globe2}
        title="Airport Heatmap"
        subtitle="Where travellers are asking to go, and where from"
        accent="amber"
        tip="Bubble size shows how many distinct schedule lookups involved each airport. Use it to spot trending routes and decide which ones to pre-warm before a demo."
      />

      {error && <ErrorCard message={error} />}

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-8 w-8 text-amber-400" />
        </div>
      ) : empty ? (
        <ChartCard title="Map">
          <Empty text="No route lookups in the cache yet." />
        </ChartCard>
      ) : (
        data && (
          <div className="space-y-6">
            <ChartCard
              title="Demand map"
              tip="Amber bubbles are departure airports and blue bubbles are destinations. Airports not in the coordinate list still appear in the rankings below."
            >
              <Plot
                data={traces}
                layout={{
                  autosize: true,
                  height: 420,
                  margin: { t: 0, b: 0, l: 0, r: 0 },
                  paper_bgcolor: "rgba(0,0,0,0)",
                  geo: {
                    bgcolor: "rgba(0,0,0,0)",
                    showland: true,
                    landcolor: "#1e293b",
                    showocean: true,
                    oceancolor: "#0b1220",
                    showcountries: true,
                    countrycolor: "#334155",
                    coastlinecolor: "#334155",
                    projection: { type: "natural earth" },
                  },
                  legend: { font: { color: "#cbd5e1" }, orientation: "h" },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: "100%" }}
                useResizeHandler
              />
            </ChartCard>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <ChartCard title="Top departures" tip="Airports people most often fly from.">
                <RankList items={data.origins} color="#fbbf24" />
              </ChartCard>
              <ChartCard title="Top destinations" tip="Airports people most often fly to.">
                <RankList items={data.destinations} color="#38bdf8" />
              </ChartCard>
              <ChartCard title="Top routes" tip="The origin to destination pairs looked up most.">
                <ul className="space-y-1.5 text-sm">
                  {data.routes.slice(0, 10).map((r) => (
                    <li key={`${r.origin}-${r.destination}`} className="flex justify-between rounded-lg bg-slate-900/60 px-3 py-2">
                      <span className="text-slate-200">
                        {r.origin} → {r.destination}
                      </span>
                      <span className="font-semibold text-amber-300">{r.count}</span>
                    </li>
                  ))}
                </ul>
              </ChartCard>
            </div>
            <p className="text-xs text-slate-500">{data.note}</p>
          </div>
        )
      )}
    </div>
  );
}
