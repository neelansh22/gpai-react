import { useEffect, useState } from "react";
import { Gauge, DollarSign, Boxes, Layers } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";
import { Card, PageHeader, Metric, Spinner } from "../../components/ui";
import FilterBar from "../../components/FilterBar";
import { usePricingState } from "../../state/PricingState";
import { pricingEndpoints } from "../../api/pricingClient";

const CORRIDOR_COLORS = { Green: "#34d399", Amber: "#facc15", Red: "#f87171" };
const CLASS_COLORS = ["#38bdf8", "#a78bfa", "#34d399", "#f472b6", "#facc15"];

function fmtCurrency(v) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `$${(v / 1000).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

export default function PricingOverview() {
  const { filters } = usePricingState();
  const [kpis, setKpis] = useState(null);
  const [pie, setPie] = useState(null);
  const [bar, setBar] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      pricingEndpoints.kpis(filters),
      pricingEndpoints.classPie(filters),
      pricingEndpoints.yearlyBar(filters),
    ])
      .then(([k, p, b]) => {
        setKpis(k.data);
        setPie(p.data);
        setBar(b.data);
      })
      .finally(() => setLoading(false));
  }, [filters]);

  return (
    <div>
      <PageHeader
        icon={Gauge}
        title="Pricing Overview"
        subtitle="High-level KPIs across the aircraft parts sales & pricing corridor dataset"
      />
      <FilterBar />

      {loading || !kpis ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-8 w-8 text-sky-400" />
        </div>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Metric label="Unique Parts" value={kpis.total_parts} accent="brand" />
            <Metric label="Records" value={kpis.total_records} accent="purple" />
            <Metric label="Total Invoice Value" value={fmtCurrency(kpis.total_invoice_value)} accent="emerald" />
            <Metric label="Avg Invoice Price" value={fmtCurrency(kpis.avg_invoice_price)} accent="amber" />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-200">
                <Layers className="h-4 w-4 text-sky-400" /> Corridor Distribution
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={Object.entries(kpis.corridor_pct).map(([name, value]) => ({ name, value }))}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                    >
                      {Object.keys(kpis.corridor_pct).map((k) => (
                        <Cell key={k} fill={CORRIDOR_COLORS[k]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }}
                      formatter={(v) => `${v}%`}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-200">
                <Boxes className="h-4 w-4 text-purple-400" /> Parts by Class
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pie?.slices || []}
                      dataKey="value"
                      nameKey="label"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                    >
                      {(pie?.slices || []).map((s, i) => (
                        <Cell key={s.label} fill={CLASS_COLORS[i % CLASS_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card className="mt-6">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-200">
              <DollarSign className="h-4 w-4 text-emerald-400" /> Invoice Value by Year
            </h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bar?.bars || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="year" stroke="#64748b" />
                  <YAxis stroke="#64748b" tickFormatter={(v) => fmtCurrency(v)} />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }}
                    formatter={(v) => fmtCurrency(v)}
                  />
                  <Bar dataKey="invoice_sum" fill="#38bdf8" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
