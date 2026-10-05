import { Card } from "../../components/ui";
import Tooltip from "../../components/Tooltip";

export function ErrorCard({ message }) {
  return (
    <Card className="mb-6 border-rose-500/30">
      <p className="text-sm font-semibold text-rose-300">Could not load monitor data</p>
      <p className="mt-1 text-xs text-slate-400">{message}</p>
      <p className="mt-2 text-xs text-slate-500">
        Check that the backend has MONITOR_WORKSPACE_ID and Azure credentials configured, and that the access key
        (if required) is entered in the sidebar.
      </p>
    </Card>
  );
}

export function ChartCard({ title, tip, children, className = "" }) {
  return (
    <Card className={className}>
      <div className="mb-3 flex items-center gap-1.5">
        <p className="text-sm font-semibold text-white">{title}</p>
        {tip && <Tooltip accent="amber" title={title} content={tip} side="bottom" />}
      </div>
      {children}
    </Card>
  );
}

export function Empty({ text = "No data in this time range yet." }) {
  return <p className="py-10 text-center text-sm text-slate-500">{text}</p>;
}

export const TOOL_COLORS = ["#fbbf24", "#34d399", "#38bdf8", "#f472b6", "#a78bfa", "#fb7185"];
