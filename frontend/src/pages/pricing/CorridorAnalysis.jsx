import { useEffect, useState } from "react";
import { ScatterChart as ScatterIcon } from "lucide-react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, PageHeader, Badge, Spinner } from "../../components/ui";
import FilterBar from "../../components/FilterBar";
import { usePricingState } from "../../state/PricingState";
import { pricingEndpoints } from "../../api/pricingClient";

const CORRIDOR_COLORS = { Green: "#34d399", Amber: "#facc15", Red: "#f87171" };

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-3 text-xs shadow-xl">
      <p className="mb-1 font-semibold text-white">{p.part_number}</p>
      <p className="text-slate-400">{p.part_class}</p>
      <p className="mt-1 text-slate-300">Invoice: ${p.x.toLocaleString()}</p>
      <p className="text-slate-300">Amber band: ${p.y.toLocaleString()}</p>
      <Badge tone={p.corridor.toLowerCase()}>{p.corridor}</Badge>
    </div>
  );
}

export default function CorridorAnalysis() {
  const { filters } = usePricingState();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    pricingEndpoints
      .scatter(filters)
      .then((res) => setData(res.data))
      .finally(() => setLoading(false));
  }, [filters]);

  const byCorridor = { Green: [], Amber: [], Red: [] };
  (data?.points || []).forEach((p) => byCorridor[p.corridor]?.push(p));

  return (
    <div>
      <PageHeader
        icon={ScatterIcon}
        title="Corridor Analysis"
        subtitle="Invoice unit price vs amber pricing band — colored by corridor status (Red / Amber / Green)"
        accent="sky"
        tip="Each dot is one transaction, plotted by invoice price against the amber pricing band. Green points sit in a healthy margin, Amber signals caution, and Red points are priced below the floor — look for clusters of Red dots to spot at-risk parts."
      />
      <FilterBar />

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-8 w-8 text-sky-400" />
        </div>
      ) : (
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm text-slate-400">{data?.count ?? 0} transactions plotted</p>
            <div className="flex gap-2">
              <Badge tone="green">Green — healthy</Badge>
              <Badge tone="amber">Amber — caution</Badge>
              <Badge tone="red">Red — at risk</Badge>
            </div>
          </div>
          <div className="h-[480px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="Invoice Unit Price"
                  stroke="#64748b"
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="Amber Price"
                  stroke="#64748b"
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
                />
                <ZAxis range={[40, 40]} />
                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />
                <Legend />
                {Object.entries(byCorridor).map(([corridor, points]) => (
                  <Scatter key={corridor} name={corridor} data={points} fill={CORRIDOR_COLORS[corridor]} opacity={0.75} />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
    </div>
  );
}
