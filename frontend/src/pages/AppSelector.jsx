import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { HeartPulse, LineChart, ArrowRight, Sparkles, Wand2 } from "lucide-react";

const APPS = [
  {
    to: "/gpai",
    icon: HeartPulse,
    title: "GP's Assistant Diagnostician",
    tagline: "AI-Powered Medical Diagnosis",
    desc: "Embeddings, 3D t-SNE clustering, and a trained ML classifier turn patient symptoms into confidence-scored diagnoses.",
    gradient: "from-brand-500 to-cyan-400",
    tags: ["Embeddings", "3D Clustering", "Classification"],
  },
  {
    to: "/pricing",
    icon: LineChart,
    title: "Dynamic Pricing Corridor",
    tagline: "Aircraft Parts Pricing Intelligence",
    desc: "A Red/Amber/Green pricing corridor dashboard for aerospace part sales — spot underpriced and at-risk transactions instantly.",
    gradient: "from-purple-500 to-pink-400",
    tags: ["Scatter Analysis", "Trend Lines", "KPI Monitoring"],
  },
  {
    to: "/sdod",
    icon: Wand2,
    title: "Synthetic Data on Demand",
    tagline: "Domain-Aware Dataset Generator",
    desc: "Describe your data in plain English and get a full relational schema, generated tables, and an explorable, augmentable dataset — instantly.",
    gradient: "from-emerald-500 to-teal-400",
    tags: ["Schema Generation", "Synthetic Data", "Business Rules"],
  },
];

export default function AppSelector() {
  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-12 text-center"
      >
        <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-slate-900/60 px-4 py-1.5 text-xs font-medium text-brand-300 ring-1 ring-brand-500/30">
          <Sparkles className="h-3.5 w-3.5" />
          Data Visualization Portfolio
        </div>
        <h1 className="text-3xl font-bold text-white sm:text-4xl">Choose an Experience</h1>
        <p className="mt-3 max-w-xl text-sm text-slate-400">
          Three interactive dashboards, one console. Pick an app below to explore.
        </p>
      </motion.div>

      <div className="grid w-full max-w-6xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {APPS.map((app, idx) => (
          <motion.div
            key={app.to}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
          >
            <Link to={app.to}>
              <div className="group relative h-full overflow-hidden rounded-3xl border border-slate-800/80 bg-slate-900/60 p-8 backdrop-blur-xl transition-all hover:-translate-y-1.5 hover:border-brand-500/40 hover:shadow-glow">
                <div
                  className={`mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${app.gradient} shadow-lg`}
                >
                  <app.icon className="h-7 w-7 text-white" />
                </div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {app.tagline}
                </p>
                <h2 className="mb-3 text-xl font-bold text-white">{app.title}</h2>
                <p className="mb-5 text-sm leading-relaxed text-slate-400">{app.desc}</p>
                <div className="mb-5 flex flex-wrap gap-2">
                  {app.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-slate-800/80 px-2.5 py-1 text-[11px] font-medium text-slate-300 ring-1 ring-slate-700"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-1.5 text-sm font-semibold text-brand-300 transition-transform group-hover:translate-x-1">
                  Launch
                  <ArrowRight className="h-4 w-4" />
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
