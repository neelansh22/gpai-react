import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ShieldCheck, ScanSearch, Regex, Cpu, FileLock2 } from "lucide-react";
import { Card, Metric, PageHeader, Badge } from "../../components/ui";
import { piiEndpoints } from "../../api/piiClient";

const FEATURES = [
  { icon: Regex, title: "Regex pass", desc: "Fast deterministic rules catch emails, phone numbers and other structured PII instantly." },
  { icon: Cpu, title: "GLiNER (ONNX) model", desc: "A quantized zero-shot NER model (small variant, onnxruntime) catches names, ages and addresses the regex pass misses." },
  { icon: FileLock2, title: "In-memory redaction", desc: "Upload a .txt/.docx/.pdf file, review detected spans, then export a redacted copy — nothing is written to disk." },
];

export default function PiiOverview() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    piiEndpoints
      .health()
      .then(({ data }) => setHealth(data))
      .catch(() => setError("Backend is waking up (free-tier cold start can take ~30-60s) — try again shortly."));
  }, []);

  return (
    <div>
      <PageHeader
        icon={ShieldCheck}
        title="int-pii"
        subtitle="A hybrid regex + GLiNER (ONNX) pipeline that finds and redacts personal data in text and documents."
        accent="rose"
        tip="Entities detected: person names, ages, street addresses, emails and phone numbers. Try the Detect & Redact page to see it live."
      />

      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Metric
          label="Model status"
          value={health ? (health.model_loaded ? "Loaded" : "Loading…") : error ? "Unavailable" : "…"}
          accent={health?.model_loaded ? "emerald" : "amber"}
        />
        <Metric label="Detection modes" value={health?.modes?.length || 3} hint={health?.modes?.join(", ") || "regex, gliner, hybrid"} />
        <Metric label="Entity types" value={health?.labels?.length || 5} hint={health?.labels?.join(", ") || "PERSON, AGE, ADDRESS, EMAIL, PHONE"} />
        <Metric label="onnxruntime" value={health?.onnxruntime || "—"} accent="purple" />
      </div>

      {error && (
        <Card className="mb-6 border-amber-500/20 bg-amber-500/5">
          <p className="text-sm text-amber-200/90">⏳ {error}</p>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {FEATURES.map((f, idx) => (
          <motion.div key={f.title} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.06 }}>
            <Card className="h-full">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-rose-500/20 to-orange-500/20 ring-1 ring-rose-500/20">
                <f.icon className="h-5 w-5 text-rose-300" />
              </div>
              <h3 className="mb-1 font-semibold text-white">{f.title}</h3>
              <p className="text-sm text-slate-400">{f.desc}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      <Card className="mt-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="mb-1 font-semibold text-white">Ready to try it?</h3>
            <p className="text-sm text-slate-400">Paste text or upload a document to see detected PII spans and export a redacted copy.</p>
          </div>
          <Link
            to="/pii/playground"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-rose-500 to-orange-400 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-rose-500/20 hover:-translate-y-0.5"
          >
            <ScanSearch className="h-4 w-4" />
            Open Playground
          </Link>
        </div>
      </Card>
      {health && (
        <p className="mt-4 text-xs text-slate-500">
          <Badge tone="green">live</Badge> <span className="ml-2">Connected to backend — {health.sizes?.join(", ")} model size(s) available.</span>
        </p>
      )}
    </div>
  );
}
