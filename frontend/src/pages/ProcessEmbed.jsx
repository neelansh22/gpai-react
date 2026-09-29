import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Cpu, Zap } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, PageHeader, Button, Metric, Spinner } from "../components/ui";
import { endpoints } from "../api/client";
import { useAppState } from "../state/AppState";

const COLORS = ["#0eb0f5", "#a855f7", "#22d3ee", "#f472b6", "#facc15", "#34d399", "#fb923c", "#818cf8"];

export default function ProcessEmbed() {
  const { status, processInfo, setProcessInfo, refreshStatus, notify } = useAppState();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleProcess = async () => {
    setLoading(true);
    try {
      const { data } = await endpoints.process();
      setProcessInfo(data);
      await refreshStatus();
      notify("Embeddings generated", "success");
    } catch (e) {
      notify(e?.response?.data?.detail || "Failed to process embeddings", "error");
    } finally {
      setLoading(false);
    }
  };

  const chartData = processInfo
    ? Object.entries(processInfo.label_distribution).map(([label, count]) => ({ label, count }))
    : [];

  return (
    <div>
      <PageHeader
        icon={Cpu}
        title="Step 2 · Process & Embed"
        subtitle="Convert patient-report text into numerical vectors for machine learning."
        tip="Each case's symptom text is converted into a numerical embedding vector using your chosen AI engine. This turns unstructured text into something a clustering or ML algorithm can actually work with. The bar chart below shows how your labels are distributed."
      />

      {!status.rows ? (
        <Card>
          <p className="text-sm text-slate-400">Load a dataset in Step 1 first.</p>
        </Card>
      ) : (
        <>
          <Card className="mb-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-200">Generate Embeddings</p>
                <p className="text-xs text-slate-500">
                  Runs offline (TF-IDF + SVD) unless a live API key was configured.
                </p>
              </div>
              <Button onClick={handleProcess} disabled={loading}>
                {loading ? <Spinner /> : <Zap className="h-4 w-4" />}
                Process Embeddings
              </Button>
            </div>
          </Card>

          {processInfo && (
            <>
              <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                <Metric label="Embedding Dim" value={processInfo.embedding_dim} />
                <Metric label="Total Samples" value={processInfo.total_samples} />
                <Metric label="Unique Diseases" value={processInfo.unique_diseases} accent="purple" />
                <Metric label="Engine" value={processInfo.provider} accent="emerald" />
              </div>

              <Card>
                <p className="mb-4 text-sm font-semibold text-slate-300">Label Distribution</p>
                <ResponsiveContainer width="100%" height={Math.max(260, chartData.length * 28)}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                    <XAxis type="number" stroke="#64748b" fontSize={12} />
                    <YAxis dataKey="label" type="category" stroke="#94a3b8" fontSize={12} width={150} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12 }}
                      labelStyle={{ color: "#e2e8f0" }}
                    />
                    <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                      {chartData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              <div className="mt-6">
                <Button onClick={() => navigate("/gpai/clusters")}>Proceed to Step 3 →</Button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
