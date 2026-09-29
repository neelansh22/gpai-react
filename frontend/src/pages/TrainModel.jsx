import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SlidersHorizontal, PlayCircle } from "lucide-react";
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

function accentForAcc(acc) {
  if (acc >= 0.85) return "#34d399";
  if (acc >= 0.6) return "#facc15";
  return "#f87171";
}

export default function TrainModel() {
  const { status, modelMetrics, setModelMetrics, refreshStatus, notify } = useAppState();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleTrain = async () => {
    setLoading(true);
    try {
      const { data } = await endpoints.train();
      setModelMetrics(data);
      await refreshStatus();
      notify("Model trained successfully", "success");
    } catch (e) {
      notify(e?.response?.data?.detail || "Training failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const perfMessage = () => {
    if (!modelMetrics) return null;
    const acc = modelMetrics.test_accuracy;
    if (acc > 0.9) return { text: "🎯 Excellent model performance!", tone: "text-emerald-300" };
    if (acc > 0.7) return { text: "👍 Good model performance!", tone: "text-brand-300" };
    return { text: "⚠️ Model may need more data or tuning.", tone: "text-amber-300" };
  };
  const perf = perfMessage();

  return (
    <div>
      <PageHeader
        icon={SlidersHorizontal}
        title="Step 4 · Train Diagnostic Model"
        subtitle="Fit a logistic regression classifier on the embedded training data."
        tip="We split your embedded cases into train/test sets and fit a classifier that learns to map symptom patterns to conditions. Test accuracy below tells you how well it generalizes to cases it hasn't seen."
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
                <p className="text-sm font-semibold text-slate-200">Train Model</p>
                <p className="text-xs text-slate-500">80/20 train-test split, standardized features.</p>
              </div>
              <Button onClick={handleTrain} disabled={loading}>
                {loading ? <Spinner /> : <PlayCircle className="h-4 w-4" />}
                Train Model
              </Button>
            </div>
          </Card>

          {modelMetrics && (
            <>
              <div className="mb-6 grid grid-cols-3 gap-4">
                <Metric
                  label="Training Accuracy"
                  value={`${(modelMetrics.training_accuracy * 100).toFixed(1)}%`}
                  accent="brand"
                />
                <Metric
                  label="Test Accuracy"
                  value={`${(modelMetrics.test_accuracy * 100).toFixed(1)}%`}
                  accent={modelMetrics.test_accuracy > 0.8 ? "emerald" : "amber"}
                />
                <Metric label="Classes" value={modelMetrics.total_classes} accent="purple" />
              </div>

              {perf && <p className={`mb-6 text-sm font-medium ${perf.tone}`}>{perf.text}</p>}

              <Card className="mb-6">
                <p className="mb-4 text-sm font-semibold text-slate-300">Per-Condition Test Accuracy</p>
                <ResponsiveContainer width="100%" height={Math.max(260, modelMetrics.per_class.length * 26)}>
                  <BarChart data={modelMetrics.per_class} layout="vertical" margin={{ left: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                    <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} stroke="#64748b" fontSize={12} />
                    <YAxis dataKey="label" type="category" stroke="#94a3b8" fontSize={12} width={160} />
                    <Tooltip
                      formatter={(v, name, props) => [`${(v * 100).toFixed(1)}% (n=${props.payload.support})`, "Accuracy"]}
                      contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12 }}
                      labelStyle={{ color: "#e2e8f0" }}
                    />
                    <Bar dataKey="accuracy" radius={[0, 6, 6, 0]}>
                      {modelMetrics.per_class.map((row, i) => (
                        <Cell key={i} fill={accentForAcc(row.accuracy)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              <Button onClick={() => navigate("/gpai/diagnose")}>Proceed to Step 5 →</Button>
            </>
          )}
        </>
      )}
    </div>
  );
}
