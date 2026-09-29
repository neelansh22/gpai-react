import { useEffect, useState } from "react";
import { Sparkles, Download, Send, RotateCcw } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Card, PageHeader, Metric, Button, Badge } from "../../components/ui";
import { useSdodState } from "../../state/SdodState";
import { sdodEndpoints } from "../../api/sdodClient";

const RULE_EXAMPLES = ["increase order_total by 10%", "decrease unit_price by 5%", "boost balance by 15%"];

export default function AugmentExplore() {
  const { status, refreshStatus, notify } = useSdodState();
  const [summary, setSummary] = useState(null);
  const [rule, setRule] = useState("");
  const [applying, setApplying] = useState(false);

  const loadSummary = () => {
    sdodEndpoints.augmentSummary().then((res) => setSummary(res.data)).catch(() => {});
  };

  useEffect(() => {
    if (status.has_data) loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status.has_data]);

  const handleApplyRule = async (e) => {
    e.preventDefault();
    if (!rule.trim()) return;
    setApplying(true);
    try {
      const { data } = await sdodEndpoints.applyRule(rule.trim());
      if (data.ok) {
        notify(data.message, "success");
        setRule("");
        loadSummary();
        refreshStatus();
      } else {
        notify(data.message, "warning");
      }
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to apply rule", "error");
    } finally {
      setApplying(false);
    }
  };

  const handleReset = async () => {
    await sdodEndpoints.resetAugmentation();
    loadSummary();
    refreshStatus();
    notify("Augmentations reset to original consolidated dataset.", "info");
  };

  if (!status.has_data) {
    return (
      <div>
        <PageHeader icon={Sparkles} title="Step 5 — Augment & Explore" subtitle="Apply business rules and explore your dataset." />
        <Card>
          <p className="text-sm text-slate-400">
            No dataset yet. Complete <strong className="text-slate-200">Generate Data</strong> first.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        icon={Sparkles}
        title="Step 5 — Augment & Explore"
        subtitle="Apply plain-English business rules, then explore distributions and correlations."
        right={
          <div className="flex gap-2">
            <a
              href={sdodEndpoints.exportConsolidatedUrl()}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-200 ring-1 ring-slate-700 hover:bg-slate-700"
            >
              <Download className="h-4 w-4" /> Export
            </a>
            <Button variant="secondary" onClick={handleReset}>
              <RotateCcw className="h-4 w-4" /> Reset
            </Button>
          </div>
        }
      />

      <Card className="mb-6">
        <form onSubmit={handleApplyRule} className="flex flex-wrap items-center gap-2">
          <input
            value={rule}
            onChange={(e) => setRule(e.target.value)}
            placeholder="e.g. increase order_total by 10%"
            className="min-w-[260px] flex-1 rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-600 focus:border-emerald-500/50 focus:outline-none"
          />
          <Button type="submit" disabled={applying || !rule.trim()}>
            <Send className="h-4 w-4" /> Apply Rule
          </Button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {RULE_EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setRule(ex)}
              className="rounded-full bg-slate-900 px-3 py-1 text-xs text-slate-400 ring-1 ring-slate-800 hover:text-slate-200"
            >
              {ex}
            </button>
          ))}
        </div>
        {status.last_rule_message && (
          <p className="mt-3 text-xs text-emerald-300">✓ {status.last_rule_message}</p>
        )}
      </Card>

      {summary && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Metric label="Rows" value={summary.rows} accent="brand" />
            <Metric label="Columns" value={summary.columns} accent="emerald" />
            <Metric label="Numeric Fields" value={summary.numeric.length} accent="purple" />
            <Metric label="Categorical Fields" value={summary.categorical.length} accent="amber" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <h3 className="mb-3 font-semibold text-white">Numeric Column Stats</h3>
              <div className="space-y-2 text-xs">
                {summary.numeric.map((n) => (
                  <div key={n.column} className="rounded-lg bg-slate-900/60 p-2.5">
                    <p className="mb-1 font-medium text-slate-200">{n.column}</p>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-slate-500">
                      <span>mean: <span className="text-slate-300">{n.mean}</span></span>
                      <span>median: <span className="text-slate-300">{n.median}</span></span>
                      <span>min: <span className="text-slate-300">{n.min}</span></span>
                      <span>max: <span className="text-slate-300">{n.max}</span></span>
                      <span>std: <span className="text-slate-300">{n.std}</span></span>
                    </div>
                  </div>
                ))}
                {summary.numeric.length === 0 && <p className="text-slate-500">No numeric columns detected.</p>}
              </div>
            </Card>

            <Card>
              <h3 className="mb-3 font-semibold text-white">Strongest Correlations</h3>
              <div className="space-y-2 text-xs">
                {summary.correlations.map((c, idx) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg bg-slate-900/60 p-2.5">
                    <span className="text-slate-300">{c.a} ↔ {c.b}</span>
                    <Badge tone={Math.abs(c.correlation) > 0.5 ? "green" : "slate"}>{c.correlation}</Badge>
                  </div>
                ))}
                {summary.correlations.length === 0 && <p className="text-slate-500">Not enough numeric columns for correlation analysis.</p>}
              </div>
            </Card>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {summary.categorical.map((cat) => (
              <Card key={cat.column}>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="font-semibold text-white">{cat.column}</h3>
                  <Badge tone="slate">{cat.unique} unique</Badge>
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={cat.top_values}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
                    <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }} />
                    <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
