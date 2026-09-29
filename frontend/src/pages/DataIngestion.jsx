import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Database, Download, UploadCloud } from "lucide-react";
import { Card, PageHeader, Button, Metric, Spinner } from "../components/ui";
import { endpoints } from "../api/client";
import { useAppState } from "../state/AppState";

const DEFAULT_URL = "https://raw.githubusercontent.com/mistralai/cookbook/main/data/Symptom2Disease.csv";

export default function DataIngestion() {
  const { dataPreview, setDataPreview, refreshStatus, notify } = useAppState();
  const [url, setUrl] = useState(DEFAULT_URL);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("url");
  const [file, setFile] = useState(null);
  const navigate = useNavigate();

  const handleLoadUrl = async () => {
    setLoading(true);
    try {
      const { data } = await endpoints.loadUrl(url);
      setDataPreview(data);
      await refreshStatus();
      notify("Dataset loaded successfully", "success");
    } catch (e) {
      notify(e?.response?.data?.detail || "Failed to load dataset", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadFile = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const { data } = await endpoints.loadFile(file);
      setDataPreview(data);
      await refreshStatus();
      notify("File loaded successfully", "success");
    } catch (e) {
      notify(e?.response?.data?.detail || "Failed to load file", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        icon={Database}
        title="Step 1 · Data Ingestion"
        subtitle="Load a symptom-to-disease dataset. Needs 'text' and 'label' columns."
      />

      <Card className="mb-6">
        <div className="mb-4 inline-flex rounded-xl bg-slate-800/60 p-1">
          <button
            onClick={() => setMode("url")}
            className={`rounded-lg px-4 py-1.5 text-sm font-medium transition ${
              mode === "url" ? "bg-brand-500/20 text-brand-200" : "text-slate-400"
            }`}
          >
            From URL
          </button>
          <button
            onClick={() => setMode("file")}
            className={`rounded-lg px-4 py-1.5 text-sm font-medium transition ${
              mode === "file" ? "bg-brand-500/20 text-brand-200" : "text-slate-400"
            }`}
          >
            Upload CSV
          </button>
        </div>

        {mode === "url" ? (
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="CSV URL"
              className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
            <Button onClick={handleLoadUrl} disabled={loading}>
              {loading ? <Spinner /> : <Download className="h-4 w-4" />}
              Load Data
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="flex flex-1 cursor-pointer items-center gap-3 rounded-xl border border-dashed border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-400 hover:border-brand-500/60">
              <UploadCloud className="h-4 w-4" />
              {file ? file.name : "Choose a CSV file..."}
              <input type="file" accept=".csv" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </label>
            <Button onClick={handleLoadFile} disabled={loading || !file}>
              {loading ? <Spinner /> : <Download className="h-4 w-4" />}
              Load Data
            </Button>
          </div>
        )}
      </Card>

      {dataPreview && (
        <>
          <div className="mb-6 grid grid-cols-3 gap-4">
            <Metric label="Total Rows" value={dataPreview.rows} />
            <Metric label="Columns" value={dataPreview.columns.length} />
            <Metric label="Unique Labels" value={dataPreview.unique_labels} accent="purple" />
          </div>

          <Card className="mb-6 overflow-hidden">
            <p className="mb-3 text-sm font-semibold text-slate-300">Data Preview (first 25 rows)</p>
            <div className="max-h-96 overflow-auto rounded-xl border border-slate-800">
              <table className="w-full min-w-[500px] text-left text-sm">
                <thead className="sticky top-0 bg-slate-900 text-slate-400">
                  <tr>
                    {dataPreview.columns.map((col) => (
                      <th key={col} className="px-4 py-2 font-medium">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dataPreview.sample.map((row, i) => (
                    <tr key={i} className="border-t border-slate-800/70 text-slate-300 hover:bg-slate-800/40">
                      {dataPreview.columns.map((col) => (
                        <td key={col} className="max-w-xs truncate px-4 py-2">
                          {String(row[col])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Button onClick={() => navigate("/gpai/process")}>Proceed to Step 2 →</Button>
        </>
      )}
    </div>
  );
}
