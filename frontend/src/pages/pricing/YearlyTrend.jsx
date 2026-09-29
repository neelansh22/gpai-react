import { useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, PageHeader, Spinner } from "../../components/ui";
import FilterBar from "../../components/FilterBar";
import { usePricingState } from "../../state/PricingState";
import { pricingEndpoints } from "../../api/pricingClient";

function fmt(v) {
  return `$${(v / 1000).toFixed(0)}K`;
}

export default function YearlyTrend() {
  const { filters } = usePricingState();
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedClass, setSelectedClass] = useState("All");

  useEffect(() => {
    setLoading(true);
    pricingEndpoints
      .trend(filters)
      .then((res) => setSeries(res.data.series || []))
      .finally(() => setLoading(false));
  }, [filters]);

  const classes = ["All", ...new Set(series.map((s) => s.part_class))];

  const filtered = selectedClass === "All" ? series : series.filter((s) => s.part_class === selectedClass);

  // Aggregate by year (average across classes if "All")
  const byYear = {};
  filtered.forEach((s) => {
    if (!byYear[s.year]) byYear[s.year] = { year: s.year, invoice: [], red: [], amber: [], green: [] };
    byYear[s.year].invoice.push(s.invoice_avg);
    byYear[s.year].red.push(s.red_avg);
    byYear[s.year].amber.push(s.amber_avg);
    byYear[s.year].green.push(s.green_avg);
  });
  const avg = (arr) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0);
  const chartData = Object.values(byYear)
    .map((y) => ({
      year: y.year,
      invoice_avg: Math.round(avg(y.invoice)),
      red_avg: Math.round(avg(y.red)),
      amber_avg: Math.round(avg(y.amber)),
      green_avg: Math.round(avg(y.green)),
    }))
    .sort((a, b) => a.year - b.year);

  return (
    <div>
      <PageHeader
        icon={TrendingUp}
        title="Yearly Trend"
        subtitle="Average invoice price against pricing corridor bands over time, by part class"
        accent="sky"
        tip="Tracks how average invoice pricing moves year over year against the Red/Amber/Green corridor bands for the selected part class. A widening gap from the green band can signal drifting pricing discipline."
      />
      <FilterBar />

      <div className="mb-4 flex flex-wrap gap-2">
        {classes.map((c) => (
          <button
            key={c}
            onClick={() => setSelectedClass(c)}
            className={`rounded-xl px-3 py-1.5 text-xs font-medium transition-colors ${
              selectedClass === c
                ? "bg-sky-500/20 text-sky-200 ring-1 ring-sky-500/40"
                : "bg-slate-900/60 text-slate-400 hover:bg-slate-800"
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-8 w-8 text-sky-400" />
        </div>
      ) : (
        <Card>
          <div className="h-[420px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="year" stroke="#64748b" />
                <YAxis stroke="#64748b" tickFormatter={fmt} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }}
                  formatter={(v) => `$${Number(v).toLocaleString()}`}
                />
                <Legend />
                <Line type="monotone" dataKey="green_avg" name="Green band" stroke="#34d399" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="amber_avg" name="Amber band" stroke="#facc15" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="red_avg" name="Red band" stroke="#f87171" strokeWidth={2} dot={false} />
                <Line
                  type="monotone"
                  dataKey="invoice_avg"
                  name="Avg invoice price"
                  stroke="#38bdf8"
                  strokeWidth={3}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
    </div>
  );
}
