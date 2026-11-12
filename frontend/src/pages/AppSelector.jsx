import { Link } from "react-router-dom";
import { HeartPulse, LineChart, ArrowUpRight, Wand2, Radar, ShieldCheck, Sparkles } from "lucide-react";

const APPS = [
  {
    to: "/gpai",
    icon: HeartPulse,
    title: "GP's Assistant Diagnostician",
    tagline: "Machine learning",
    desc: "Explore how symptom data, embeddings and a classifier can support a diagnostic workflow.",
    accent: "text-sky-300 bg-sky-400/10 ring-sky-400/20",
    tags: ["NLP", "Classification", "Interactive demo"],
  },
  {
    to: "/pricing",
    icon: LineChart,
    title: "Dynamic Pricing Corridor",
    tagline: "Decision intelligence",
    desc: "Explore aircraft parts pricing through interactive corridors, trends and transaction-level analysis.",
    accent: "text-violet-300 bg-violet-400/10 ring-violet-400/20",
    tags: ["Analytics", "Pricing", "Visualisation"],
  },
  {
    to: "/sdod",
    icon: Wand2,
    title: "Synthetic Data on Demand",
    tagline: "Data generation",
    desc: "Turn a plain-language data request into a relational schema and an explorable synthetic dataset.",
    accent: "text-emerald-300 bg-emerald-400/10 ring-emerald-400/20",
    tags: ["Synthetic data", "Schemas", "Business rules"],
  },
  {
    to: "/monitor",
    icon: Radar,
    title: "Skyline Monitor",
    tagline: "Observability",
    desc: "A closer look at voice-agent usage, cache performance and demand across airports.",
    accent: "text-amber-300 bg-amber-400/10 ring-amber-400/20",
    tags: ["Telemetry", "APIs", "Monitoring"],
  },
  {
    to: "/pii",
    icon: ShieldCheck,
    title: "int-pii",
    tagline: "Privacy engineering",
    desc: "Detect, review and redact personal information using rules and a compact language model.",
    accent: "text-rose-300 bg-rose-400/10 ring-rose-400/20",
    tags: ["Entity recognition", "Documents", "ONNX"],
  },
];

export default function AppSelector() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-6 pb-16 pt-8 sm:px-10 lg:px-14">
      <header className="flex items-center justify-between border-b border-slate-800/80 pb-6">
        <div className="flex items-center gap-2.5 text-sm font-semibold tracking-wide text-slate-200">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700 bg-slate-900">
            <Sparkles className="h-4 w-4 text-sky-300" aria-hidden="true" />
          </span>
          Portfolio
        </div>
        <span className="text-right text-xs text-slate-500">An engineered approach towards AI alignment.</span>
      </header>

      <section className="max-w-3xl py-16 sm:py-20" aria-labelledby="portfolio-heading">
        <p className="mb-5 text-xs font-semibold uppercase tracking-[0.2em] text-sky-300">Ideas, built and explored</p>
        <h1 id="portfolio-heading" className="text-4xl font-semibold leading-tight tracking-tight text-white sm:text-5xl">
          Programme Heavy Harness
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-slate-400 sm:text-lg">
          These proofs of concept combine thoughtful software engineering, compact models
          and deliberate design, with room for larger AI models where they add value.
          The focus is on privacy, practical outcomes and using tokens economically.
        </p>
      </section>

      <section aria-labelledby="projects-heading">
        <div className="mb-6 flex items-end justify-between border-b border-slate-800/80 pb-4">
          <div>
            <p className="mb-1 text-xs uppercase tracking-[0.18em] text-slate-500">Selected work</p>
            <h2 id="projects-heading" className="text-xl font-semibold text-white">Explore the projects</h2>
          </div>
          <span className="text-xs text-slate-500">Interactive demos</span>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {APPS.map((app) => (
            <Link
              key={app.to}
              to={app.to}
              className="group flex min-h-64 flex-col rounded-2xl border border-slate-800/80 bg-slate-900/50 p-6 transition duration-200 hover:-translate-y-1 hover:border-slate-600 hover:bg-slate-900/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sky-300"
            >
              <div className="mb-6 flex items-start justify-between">
                <span className={`flex h-11 w-11 items-center justify-center rounded-xl ring-1 ${app.accent}`}>
                  <app.icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <ArrowUpRight className="h-4 w-4 text-slate-600 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-slate-200" aria-hidden="true" />
              </div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">{app.tagline}</p>
              <h3 className="text-lg font-semibold text-slate-100">{app.title}</h3>
              <p className="mt-2 flex-1 text-sm leading-6 text-slate-400">{app.desc}</p>
              <div className="mt-6 flex flex-wrap gap-2">
                {app.tags.map((tag) => (
                  <span key={tag} className="rounded-md border border-slate-800 bg-slate-950/50 px-2 py-1 text-[11px] text-slate-400">{tag}</span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      </section>
      <footer className="mt-12 border-t border-slate-800/80 pt-6 text-xs leading-5 text-slate-500">
        Experiments for learning and exploration. Some services may take a moment to wake up.
      </footer>
    </main>
  );
}
