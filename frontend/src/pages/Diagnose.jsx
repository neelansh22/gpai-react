import { useState } from "react";
import { motion } from "framer-motion";
import { Stethoscope, Search } from "lucide-react";
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
import { Card, PageHeader, Button, Badge, Spinner } from "../components/ui";
import { endpoints } from "../api/client";
import { useAppState } from "../state/AppState";

const EXAMPLES = [
  "Patient reports severe headache, nausea, sensitivity to light, and blurred vision.",
  "Fever, cough, fatigue and shortness of breath for the past 3 days.",
  "Joint pain, swelling and stiffness in both knees, worse in the morning.",
  "Burning sensation during urination and frequent urge to go.",
];

const toneColor = { green: "#34d399", amber: "#facc15", red: "#f87171" };

export default function Diagnose() {
  const { status, diagnosis, setDiagnosis, notify } = useAppState();
  const [symptoms, setSymptoms] = useState("");
  const [loading, setLoading] = useState(false);

  const handleDiagnose = async () => {
    if (!symptoms.trim()) return;
    setLoading(true);
    try {
      const { data } = await endpoints.diagnose(symptoms);
      setDiagnosis(data);
      notify("Diagnosis generated", "success");
    } catch (e) {
      notify(e?.response?.data?.detail || "Diagnosis failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const chartData = diagnosis?.top_predictions.map((p) => ({
    label: p.label,
    probability: p.probability,
  }));

  return (
    <div>
      <PageHeader
        icon={Stethoscope}
        title="Step 5 · Enter Symptoms & Diagnose"
        subtitle="The trained model analyzes symptom text and returns a confidence-scored diagnosis."
        tip="Describe symptoms in plain English. The trained model embeds your text the same way as the training data and ranks the most likely conditions by confidence — this is a demo, not medical advice."
      />

      {!status.trained ? (
        <Card>
          <p className="text-sm text-slate-400">Train the model in Step 4 first.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <textarea
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              rows={5}
              placeholder="e.g., Patient reports severe headache, nausea, sensitivity to light, and blurred vision..."
              className="w-full resize-none rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-200 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
            <div className="mt-3 flex justify-end">
              <Button onClick={handleDiagnose} disabled={loading || !symptoms.trim()}>
                {loading ? <Spinner /> : <Search className="h-4 w-4" />}
                Diagnose
              </Button>
            </div>
          </Card>

          <Card>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Example Symptoms
            </p>
            <div className="space-y-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => setSymptoms(ex)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-left text-xs text-slate-400 hover:border-brand-500/40 hover:text-slate-200"
                >
                  {ex}
                </button>
              ))}
            </div>
          </Card>
        </div>
      )}

      {diagnosis && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-6 space-y-6">
          <Card className="border-brand-500/30 bg-gradient-to-br from-brand-500/10 to-purple-500/5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Diagnosis</p>
                <h2 className="mt-1 text-2xl font-bold text-white">{diagnosis.diagnosis}</h2>
              </div>
              <div className="text-right">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Confidence</p>
                <p className="mt-1 text-2xl font-bold" style={{ color: toneColor[diagnosis.confidence_color] }}>
                  {(diagnosis.confidence * 100).toFixed(1)}%
                </p>
                <Badge tone={diagnosis.confidence_color}>{diagnosis.confidence_color.toUpperCase()}</Badge>
              </div>
            </div>
          </Card>

          <Card>
            <p className="mb-4 text-sm font-semibold text-slate-300">Top Predicted Conditions</p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} stroke="#64748b" fontSize={12} />
                <YAxis dataKey="label" type="category" stroke="#94a3b8" fontSize={12} width={160} />
                <Tooltip
                  formatter={(v) => [`${(v * 100).toFixed(1)}%`, "Probability"]}
                  contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12 }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="probability" radius={[0, 6, 6, 0]}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={i === 0 ? "#0eb0f5" : "#334155"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <p className="mb-3 text-sm font-semibold text-slate-300">
              Medical Information — {diagnosis.medical_info.condition}
            </p>
            <p className="mb-4 text-sm text-slate-400">{diagnosis.medical_info.description}</p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {[
                ["Common Causes", diagnosis.medical_info.common_causes],
                ["Symptoms", diagnosis.medical_info.symptoms],
                ["Preventive Measures", diagnosis.medical_info.preventive_measures],
                ["Immediate Relief", diagnosis.medical_info.immediate_relief],
              ].map(([title, items]) => (
                <div key={title} className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-brand-300">{title}</p>
                  <ul className="space-y-1 text-sm text-slate-400">
                    {items.map((item) => (
                      <li key={item} className="flex gap-2">
                        <span className="text-brand-400">•</span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </Card>

          <Card className="border-amber-500/20 bg-amber-500/5">
            <p className="text-sm text-amber-200/90">
              ⚠️ This is an AI assistant for educational purposes only. Always consult a qualified
              healthcare professional for diagnosis and treatment.
            </p>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
