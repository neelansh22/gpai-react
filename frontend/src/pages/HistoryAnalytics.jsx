import { useEffect, useState } from "react";
import { History as HistoryIcon, Trash2, RefreshCcw } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, PageHeader, Button, Badge } from "../components/ui";
import { endpoints } from "../api/client";
import { useAppState } from "../state/AppState";

const TONE_COLOR = { green: "#34d399", amber: "#facc15", red: "#f87171" };

export default function HistoryAnalytics() {
  const { history, refreshHistory, notify } = useAppState();
  const [analysis, setAnalysis] = useState([]);
  const [thresholds, setThresholds] = useState({ green: [75, 100], amber: [55, 74], red: [0, 54] });

  const load = async () => {
    await refreshHistory();
    try {
      const { data } = await endpoints.historyAnalysis();
      setAnalysis(data.analysis || []);
    } catch (e) {
      /* ignore */
    }
    try {
      const { data } = await endpoints.getThresholds();
      setThresholds(data);
    } catch (e) {
      /* ignore */
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleClear = async () => {
    await endpoints.clearHistory();
    notify("History cleared", "info");
    load();
  };

  const pieData = [
    { name: "Green (High)", value: history.filter((h) => h.color === "green").length, color: "#34d399" },
    { name: "Amber (Medium)", value: history.filter((h) => h.color === "amber").length, color: "#facc15" },
    { name: "Red (Low)", value: history.filter((h) => h.color === "red").length, color: "#f87171" },
  ].filter((d) => d.value > 0);

  const saveThresholds = async () => {
    try {
      await endpoints.setThresholds(thresholds);
      notify("Thresholds updated", "success");
      load();
    } catch (e) {
      notify("Failed to update thresholds", "error");
    }
  };

  return (
    <div>
      <PageHeader
        icon={HistoryIcon}
        title="Search History & Analytics"
        subtitle="Review past diagnoses and confidence-band analytics across conditions."
        tip="Every diagnosis you run is logged here. Use this to audit past queries, tune confidence thresholds, and see analytics on which conditions come up most often and how confident the model was."
        right={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={load}>
              <RefreshCcw className="h-4 w-4" /> Refresh
            </Button>
            <Button variant="danger" onClick={handleClear}>
              <Trash2 className="h-4 w-4" /> Clear
            </Button>
          </div>
        }
      />

      {history.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-400">No diagnoses yet — try Step 5 to build up history.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <p className="mb-4 text-sm font-semibold text-slate-300">Confidence Breakdown by Condition</p>
            <ResponsiveContainer width="100%" height={Math.max(240, analysis.length * 34)}>
              <BarChart data={analysis} layout="vertical" margin={{ left: 24 }} stackOffset="expand">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" tickFormatter={(v) => `${Math.round(v * 100)}%`} stroke="#64748b" fontSize={12} />
                <YAxis dataKey="condition" type="category" stroke="#94a3b8" fontSize={12} width={150} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12 }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Legend />
                <Bar dataKey="green_pct" stackId="a" name="Green %" fill="#34d399" radius={[0, 0, 0, 0]} />
                <Bar dataKey="amber_pct" stackId="a" name="Amber %" fill="#facc15" />
                <Bar dataKey="red_pct" stackId="a" name="Red %" fill="#f87171" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <p className="mb-4 text-sm font-semibold text-slate-300">Overall Confidence Distribution</p>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={3}>
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12 }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Card>

          <Card className="lg:col-span-3">
            <p className="mb-3 text-sm font-semibold text-slate-300">Recent Diagnoses</p>
            <div className="max-h-80 space-y-2 overflow-auto">
              {history
                .slice()
                .reverse()
                .map((entry, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/50 p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-slate-300">{entry.input_text}</p>
                      <p className="text-xs text-slate-500">{entry.timestamp}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-slate-200">{entry.prediction}</span>
                      <span className="text-sm font-bold" style={{ color: TONE_COLOR[entry.color] }}>
                        {(entry.confidence * 100).toFixed(1)}%
                      </span>
                      <Badge tone={entry.color}>{entry.color}</Badge>
                    </div>
                  </div>
                ))}
            </div>
          </Card>

          <Card className="lg:col-span-3">
            <p className="mb-4 text-sm font-semibold text-slate-300">Customize Confidence Thresholds (%)</p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {(["green", "amber", "red"]).map((key) => (
                <div key={key} className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider" style={{ color: TONE_COLOR[key] }}>
                    {key}
                  </p>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={thresholds[key][0]}
                      onChange={(e) =>
                        setThresholds((t) => ({ ...t, [key]: [Number(e.target.value), t[key][1]] }))
                      }
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200"
                    />
                    <span className="text-slate-500">–</span>
                    <input
                      type="number"
                      value={thresholds[key][1]}
                      onChange={(e) =>
                        setThresholds((t) => ({ ...t, [key]: [t[key][0], Number(e.target.value)] }))
                      }
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200"
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4">
              <Button onClick={saveThresholds}>Save Thresholds</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
