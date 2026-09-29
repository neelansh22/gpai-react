import { useEffect } from "react";
import { motion } from "framer-motion";
import { Activity, Boxes, Cpu, Database, SlidersHorizontal, Stethoscope } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, Metric, PageHeader } from "../components/ui";
import { useAppState } from "../state/AppState";

const STEPS = [
  { to: "/data", icon: Database, title: "Data Ingestion", desc: "Load a symptom-to-disease dataset from URL or CSV upload." },
  { to: "/process", icon: Cpu, title: "Process & Embed", desc: "Vectorize patient-report text into numerical embeddings." },
  { to: "/clusters", icon: Boxes, title: "Cluster Visualization", desc: "Explore an interactive 3D t-SNE map of condition clusters." },
  { to: "/train", icon: SlidersHorizontal, title: "Train Model", desc: "Fit a logistic regression diagnostic classifier." },
  { to: "/diagnose", icon: Stethoscope, title: "Diagnose", desc: "Enter symptoms and get a confidence-scored diagnosis." },
];

export default function Overview() {
  const { status, refreshStatus } = useAppState();

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  return (
    <div>
      <PageHeader
        icon={Activity}
        title="GP's Assistant Diagnostician"
        subtitle="A modern, data-driven diagnostic pipeline — embeddings, clustering, and machine learning in one sleek console."
      />

      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Metric label="Patients / Rows" value={status.rows || 0} accent="brand" />
        <Metric label="Embeddings" value={status.processed ? "Ready" : "Pending"} accent={status.processed ? "emerald" : "amber"} />
        <Metric label="Clusters" value={status.has_clusters ? "Rendered" : "Pending"} accent={status.has_clusters ? "emerald" : "amber"} />
        <Metric label="Model" value={status.trained ? "Trained" : "Untrained"} accent={status.trained ? "emerald" : "amber"} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {STEPS.map((step, idx) => (
          <motion.div
            key={step.to}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.06 }}
          >
            <Link to={step.to}>
              <Card className="group h-full cursor-pointer transition-all hover:-translate-y-1 hover:ring-1 hover:ring-brand-500/40">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500/20 to-purple-500/20 ring-1 ring-brand-500/20">
                  <step.icon className="h-5 w-5 text-brand-300" />
                </div>
                <h3 className="mb-1 font-semibold text-white">
                  {idx + 1}. {step.title}
                </h3>
                <p className="text-sm text-slate-400">{step.desc}</p>
              </Card>
            </Link>
          </motion.div>
        ))}
      </div>

      <Card className="mt-6 border-amber-500/20 bg-amber-500/5">
        <p className="text-sm text-amber-200/90">
          ⚠️ <strong>Medical Disclaimer:</strong> This application is for educational and portfolio
          purposes only. It is not a substitute for professional medical advice, diagnosis, or
          treatment.
        </p>
      </Card>
    </div>
  );
}
