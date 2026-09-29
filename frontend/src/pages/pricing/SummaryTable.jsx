import { useEffect, useState } from "react";
import { Table2 } from "lucide-react";
import { Card, PageHeader, Badge, Spinner } from "../../components/ui";
import FilterBar from "../../components/FilterBar";
import { usePricingState } from "../../state/PricingState";
import { pricingEndpoints } from "../../api/pricingClient";

function fmtCurrency(v) {
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (Math.abs(v) >= 1_000) return `$${(v / 1000).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

const TONE = { Green: "green", Amber: "amber", Red: "red" };

export default function SummaryTable() {
  const { filters } = usePricingState();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    pricingEndpoints
      .table(filters)
      .then((res) => setRows(res.data.rows || []))
      .finally(() => setLoading(false));
  }, [filters]);

  return (
    <div>
      <PageHeader
        icon={Table2}
        title="Corridor Summary Table"
        subtitle="Aggregated part counts and pricing band totals grouped by corridor status"
      />
      <FilterBar />

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-8 w-8 text-sky-400" />
        </div>
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500">
                <th className="px-5 py-3">Corridor</th>
                <th className="px-5 py-3">Part Count</th>
                <th className="px-5 py-3">Invoice Sum</th>
                <th className="px-5 py-3">Red Sum</th>
                <th className="px-5 py-3">Amber Sum</th>
                <th className="px-5 py-3">Green Sum</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-500">
                    No records match the current filters.
                  </td>
                </tr>
              ) : (
                rows.map((r) => (
                  <tr key={r.corridor} className="border-b border-slate-800/60 hover:bg-slate-900/40">
                    <td className="px-5 py-3">
                      <Badge tone={TONE[r.corridor] || "slate"}>{r.corridor}</Badge>
                    </td>
                    <td className="px-5 py-3 text-slate-300">{r.part_count}</td>
                    <td className="px-5 py-3 font-medium text-white">{fmtCurrency(r.invoice_sum)}</td>
                    <td className="px-5 py-3 text-rose-300">{fmtCurrency(r.red_sum)}</td>
                    <td className="px-5 py-3 text-amber-300">{fmtCurrency(r.amber_sum)}</td>
                    <td className="px-5 py-3 text-emerald-300">{fmtCurrency(r.green_sum)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
