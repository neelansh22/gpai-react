import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Plot from "react-plotly.js";
import { Boxes, Sparkles } from "lucide-react";
import { Card, PageHeader, Button, Metric, Spinner } from "../components/ui";
import { endpoints } from "../api/client";
import { useAppState } from "../state/AppState";

const PALETTE = [
  "#0eb0f5", "#a855f7", "#22d3ee", "#f472b6", "#facc15",
  "#34d399", "#fb923c", "#818cf8", "#f87171", "#4ade80",
  "#38bdf8", "#e879f9", "#fbbf24", "#2dd4bf", "#c084fc",
];

export default function Clusters() {
  const { status, clusterData, setClusterData, refreshStatus, notify } = useAppState();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleCluster = async () => {
    setLoading(true);
    try {
      const { data } = await endpoints.cluster();
      setClusterData(data);
      await refreshStatus();
      notify("3D cluster map generated", "success");
    } catch (e) {
      notify(e?.response?.data?.detail || "Failed to generate clusters", "error");
    } finally {
      setLoading(false);
    }
  };

  const traces = useMemo(() => {
    if (!clusterData) return [];
    const byLabel = new Map();
    clusterData.points.forEach((p) => {
      if (!byLabel.has(p.label)) byLabel.set(p.label, []);
      byLabel.get(p.label).push(p);
    });
    return Array.from(byLabel.entries()).map(([label, points], idx) => ({
      x: points.map((p) => p.x),
      y: points.map((p) => p.y),
      z: points.map((p) => p.z),
      text: points.map((p) => `${label}<br>${p.text}`),
      hovertemplate: "%{text}<extra></extra>",
      mode: "markers",
      type: "scatter3d",
      name: label,
      marker: {
        size: 4.5,
        color: PALETTE[idx % PALETTE.length],
        opacity: 0.85,
        line: { width: 0 },
      },
    }));
  }, [clusterData]);

  return (
    <div>
      <PageHeader
        icon={Boxes}
        title="Step 3 · 3D Cluster Visualization"
        subtitle="t-SNE dimensionality reduction reveals how medical conditions naturally group together."
        tip="Each point is one case, projected from high-dimensional embeddings down to 3D. Points that cluster tightly together represent conditions with similar symptom patterns — drag to rotate, scroll to zoom, and hover a point for details."
      />

      {!status.processed ? (
        <Card>
          <p className="text-sm text-slate-400">Process embeddings in Step 2 first.</p>
        </Card>
      ) : (
        <>
          <Card className="mb-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-200">Generate t-SNE Clusters</p>
                <p className="text-xs text-slate-500">Reduces high-dimensional embeddings to 3D space.</p>
              </div>
              <Button onClick={handleCluster} disabled={loading}>
                {loading ? <Spinner /> : <Sparkles className="h-4 w-4" />}
                Generate Clusters
              </Button>
            </div>
          </Card>

          {clusterData && (
            <>
              <div className="mb-6 grid grid-cols-3 gap-4">
                <Metric label="Total Clusters" value={clusterData.total_clusters} accent="purple" />
                <Metric label="Data Points" value={clusterData.data_points} />
                <Metric label="Dim Reduction" value={`${clusterData.original_dim} → 3`} accent="emerald" />
              </div>

              <Card className="mb-6">
                <Plot
                  data={traces}
                  layout={{
                    autosize: true,
                    height: 620,
                    paper_bgcolor: "rgba(0,0,0,0)",
                    plot_bgcolor: "rgba(0,0,0,0)",
                    font: { color: "#cbd5e1", size: 11 },
                    margin: { l: 0, r: 0, b: 0, t: 20 },
                    legend: { bgcolor: "rgba(15,23,42,0.6)", bordercolor: "#1e293b", borderwidth: 1 },
                    scene: {
                      xaxis: { title: "t-SNE 1", gridcolor: "#1e293b", zerolinecolor: "#334155", backgroundcolor: "rgba(0,0,0,0)" },
                      yaxis: { title: "t-SNE 2", gridcolor: "#1e293b", zerolinecolor: "#334155", backgroundcolor: "rgba(0,0,0,0)" },
                      zaxis: { title: "t-SNE 3", gridcolor: "#1e293b", zerolinecolor: "#334155", backgroundcolor: "rgba(0,0,0,0)" },
                    },
                  }}
                  config={{ displaylogo: false, responsive: true }}
                  style={{ width: "100%" }}
                  useResizeHandler
                />
              </Card>

              <Button onClick={() => navigate("/gpai/train")}>Proceed to Step 4 →</Button>
            </>
          )}
        </>
      )}
    </div>
  );
}
