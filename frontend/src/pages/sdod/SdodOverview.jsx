import { useEffect } from "react";
import { motion } from "framer-motion";
import { Wand2, MessageSquareText, Network, PencilRuler, Database, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, Metric, PageHeader } from "../../components/ui";
import { useSdodState } from "../../state/SdodState";

const STEPS = [
  { to: "/sdod/intent", icon: MessageSquareText, title: "Define Intent", desc: "Describe the dataset you need in plain English — we detect the domain and ask 3 quick calibration questions." },
  { to: "/sdod/schema", icon: Network, title: "Build Schema", desc: "Instantly generate a relational schema (tables, columns, keys, relationships) tailored to your answers." },
  { to: "/sdod/editor", icon: PencilRuler, title: "Edit Schema", desc: "Fine-tune table and column definitions, or upload your own schema JSON." },
  { to: "/sdod/generate", icon: Database, title: "Generate Data", desc: "Produce realistic rows for every table and auto-consolidate them via foreign keys." },
  { to: "/sdod/augment", icon: Sparkles, title: "Augment & Explore", desc: "Apply plain-English business rules and explore distributions, correlations, and top categories." },
];

export default function SdodOverview() {
  const { status, refreshStatus } = useSdodState();

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  return (
    <div>
      <PageHeader
        icon={Wand2}
        title="Synthetic Data on Demand"
        subtitle="Describe it. Shape it. Generate it. A domain-aware synthetic dataset engine — zero API keys, instant results."
        accent="emerald"
        tip="Track your progress through the 5-step pipeline: describe your intent, build a schema, refine it, generate rows, then apply business rules. Optionally connect OpenAI or Gemini in the sidebar for an AI-generated 'online' flavor."
      />

      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Metric label="Domain" value={status.domain ? status.domain : "—"} accent="brand" />
        <Metric label="Tables" value={status.table_count || 0} accent={status.has_schema ? "emerald" : "amber"} />
        <Metric label="Dataset Rows" value={status.consolidated_rows || 0} accent={status.has_data ? "emerald" : "amber"} />
        <Metric label="Augmented" value={status.has_augmented ? "Ready" : "Pending"} accent={status.has_augmented ? "emerald" : "amber"} />
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
              <Card className="group h-full cursor-pointer transition-all hover:-translate-y-1 hover:ring-1 hover:ring-emerald-500/40">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 ring-1 ring-emerald-500/20">
                  <step.icon className="h-5 w-5 text-emerald-300" />
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

      <Card className="mt-6 border-emerald-500/20 bg-emerald-500/5">
        <p className="text-sm text-emerald-200/90">
          💡 <strong>How it works:</strong> Instead of calling an external LLM for every step (slow, flaky, needs an
          API key), this engine uses a fast domain-aware template system — same 5-step workflow, instant and fully
          self-contained.
        </p>
      </Card>
    </div>
  );
}
