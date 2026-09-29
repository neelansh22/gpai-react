import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Database, Download, ArrowRight, Loader2 } from "lucide-react";
import { Card, PageHeader, Metric, Button, Badge } from "../../components/ui";
import { useSdodState } from "../../state/SdodState";
import { sdodEndpoints } from "../../api/sdodClient";

const ROW_OPTIONS = [40, 120, 400];

export default function GenerateData() {
  const { status, generateData, notify } = useSdodState();
  const [rows, setRows] = useState(status.rows_per_table || 120);
  const [loading, setLoading] = useState(false);
  const [activeTable, setActiveTable] = useState(null);
  const [preview, setPreview] = useState(null);
  const navigate = useNavigate();

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const data = await generateData(rows);
      const firstTable = data.table_names?.[0] || null;
      setActiveTable(firstTable);
      notify(`Generated data for ${data.table_names?.length || 0} tables.`, "success");
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to generate data — check your schema first.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (status.has_data && !activeTable) {
      setActiveTable(status.table_names?.[0] || null);
    }
  }, [status.has_data, status.table_names, activeTable]);

  useEffect(() => {
    if (activeTable) {
      sdodEndpoints.previewTable(activeTable, 15).then((res) => setPreview(res.data)).catch(() => {});
    }
  }, [activeTable]);

  if (!status.has_schema) {
    return (
      <div>
        <PageHeader icon={Database} title="Step 4 — Generate Data" subtitle="Produce rows for every table in your schema." accent="emerald" tip="You'll need a schema before generating data — complete Step 2 or 3 first." />
        <Card>
          <p className="text-sm text-slate-400">
            No schema available yet. Complete <strong className="text-slate-200">Build Schema</strong> or{" "}
            <strong className="text-slate-200">Edit Schema</strong> first.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        icon={Database}
        title="Step 4 — Generate Data"
        subtitle="Rows are generated for every table and automatically joined via foreign keys."
        accent="emerald"
        tip="Pick how many rows per table and generate. Related tables are automatically linked through their foreign keys, so the data stays referentially consistent. Preview any table below before moving to augmentation."
        right={
          <div className="flex items-center gap-2">
            <select
              value={rows}
              onChange={(e) => setRows(Number(e.target.value))}
              className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 focus:border-emerald-500/50 focus:outline-none"
            >
              {ROW_OPTIONS.map((r) => (
                <option key={r} value={r}>{r} rows/table</option>
              ))}
            </select>
            <Button onClick={handleGenerate} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
              Generate
            </Button>
          </div>
        }
      />

      {status.has_data && (
        <>
          <div className="mb-6 grid grid-cols-3 gap-4">
            <Metric label="Tables Generated" value={status.table_names?.length || 0} accent="brand" />
            <Metric label="Consolidated Rows" value={status.consolidated_rows} accent="emerald" />
            <Metric label="Consolidated Columns" value={status.consolidated_cols} accent="purple" />
          </div>

          <Card className="mb-6">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-2">
                {status.table_names?.map((name) => (
                  <button
                    key={name}
                    onClick={() => setActiveTable(name)}
                    className={`rounded-full px-3 py-1.5 text-xs font-medium ring-1 ${
                      activeTable === name
                        ? "bg-emerald-500/20 text-emerald-200 ring-emerald-500/40"
                        : "bg-slate-900 text-slate-400 ring-slate-800 hover:text-slate-200"
                    }`}
                  >
                    {name}
                  </button>
                ))}
              </div>
              {activeTable && (
                <a
                  href={sdodEndpoints.exportTableUrl(activeTable)}
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-emerald-300"
                >
                  <Download className="h-3.5 w-3.5" /> Export {activeTable}.csv
                </a>
              )}
            </div>

            {preview && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-500">
                      {preview.columns.map((c) => (
                        <th key={c} className="px-2 py-2 font-medium">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, idx) => (
                      <tr key={idx} className="border-b border-slate-900/60 text-slate-300">
                        {preview.columns.map((c) => (
                          <td key={c} className="px-2 py-1.5">{String(row[c] ?? "")}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-2 text-[11px] text-slate-500">
                  Showing {preview.rows.length} of {preview.total_rows} rows.
                </p>
              </div>
            )}
          </Card>

          <div className="mb-6 flex items-center gap-3">
            <a
              href={sdodEndpoints.exportConsolidatedUrl()}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-200 ring-1 ring-slate-700 hover:bg-slate-700"
            >
              <Download className="h-4 w-4" /> Export Consolidated Dataset (CSV)
            </a>
            <Badge tone="green">{status.consolidated_rows} rows joined</Badge>
          </div>

          <Button onClick={() => navigate("/sdod/augment")}>
            Continue to Augment & Explore
            <ArrowRight className="h-4 w-4" />
          </Button>
        </>
      )}
    </div>
  );
}
