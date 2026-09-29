import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquareText, ArrowRight, Loader2 } from "lucide-react";
import { Card, PageHeader, Button, Badge } from "../../components/ui";
import { useSdodState } from "../../state/SdodState";

const EXAMPLES = [
  "Customer data for an e-commerce platform selling electronics with order history",
  "Employee records for a mid-size tech company with departments and payroll",
  "Product catalog and inventory for a retail supplier network",
  "Bank account and transaction data for a retail banking app",
];

export default function IntentWizard() {
  const { questions, submitIntent, submitAnswers, notify } = useSdodState();
  const [intent, setIntent] = useState("");
  const [loading, setLoading] = useState(false);
  const [answers, setAnswers] = useState({});
  const navigate = useNavigate();

  const handleSubmitIntent = async (e) => {
    e.preventDefault();
    if (!intent.trim()) return;
    setLoading(true);
    try {
      await submitIntent(intent.trim());
      setAnswers({});
      notify("Clarifying questions ready — pick your answers below.", "success");
    } catch (err) {
      notify(err?.response?.data?.detail || "Failed to analyze intent", "error");
    } finally {
      setLoading(false);
    }
  };

  const selectAnswer = (key, value) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  };

  const handleContinue = async () => {
    try {
      await submitAnswers(answers);
      notify("Answers saved — build your schema next.", "success");
      navigate("/sdod/schema");
    } catch (err) {
      notify("Failed to save answers", "error");
    }
  };

  const allAnswered = questions.length > 0 && questions.every((q) => answers[q.key]);

  return (
    <div>
      <PageHeader
        icon={MessageSquareText}
        title="Step 1 — Define Your Data Intent"
        subtitle="Describe the dataset you want in plain English. We detect the domain and ask a few calibration questions."
        accent="emerald"
        tip="Just describe what you need, e.g. 'e-commerce orders for a mid-size retailer'. We auto-detect the domain (ecommerce, HR, financial, etc.) and ask a couple of quick questions to calibrate scale and realism before building a schema."
      />

      <Card className="mb-6">
        <form onSubmit={handleSubmitIntent} className="space-y-3">
          <label className="text-sm font-medium text-slate-300">Describe your dataset</label>
          <textarea
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            rows={3}
            placeholder="e.g. Customer data for an e-commerce platform selling electronics with order history and product reviews"
            className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-200 placeholder:text-slate-600 focus:border-emerald-500/50 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
          />
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                type="button"
                key={ex}
                onClick={() => setIntent(ex)}
                className="rounded-full bg-slate-900 px-3 py-1 text-xs text-slate-400 ring-1 ring-slate-800 hover:text-slate-200"
              >
                {ex.slice(0, 42)}…
              </button>
            ))}
          </div>
          <Button type="submit" disabled={loading || !intent.trim()}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageSquareText className="h-4 w-4" />}
            Analyze Intent
          </Button>
        </form>
      </Card>

      {questions.length > 0 && (
        <Card>
          <h3 className="mb-4 font-semibold text-white">Calibration Questions</h3>
          <div className="space-y-5">
            {questions.map((q) => (
              <div key={q.key}>
                <p className="mb-2 text-sm font-medium text-slate-200">{q.question}</p>
                <div className="flex flex-wrap gap-2">
                  {q.options.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => selectAnswer(q.key, opt)}
                      className={`rounded-xl px-3 py-2 text-xs font-medium ring-1 transition-all ${
                        answers[q.key] === opt
                          ? "bg-emerald-500/20 text-emerald-200 ring-emerald-500/40"
                          : "bg-slate-900 text-slate-400 ring-slate-800 hover:text-slate-200"
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex items-center gap-3">
            <Button onClick={handleContinue} disabled={!allAnswered}>
              Continue to Schema
              <ArrowRight className="h-4 w-4" />
            </Button>
            {allAnswered && <Badge tone="green">Ready</Badge>}
          </div>
        </Card>
      )}
    </div>
  );
}
