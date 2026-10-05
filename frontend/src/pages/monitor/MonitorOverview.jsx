import { useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, DatabaseZap, Gauge, Globe2, Mic, Radar } from "lucide-react";
import { Card, Metric, PageHeader, Spinner } from "../../components/ui";
import { monitorEndpoints } from "../../api/monitorClient";
import { useMonitorData } from "../../state/useMonitorData";
import { useMonitorState } from "../../state/MonitorState";
import { ChartCard, Empty, ErrorCard } from "./shared";

const GUIDE = [
  {
    to: "/monitor/cache",
    icon: DatabaseZap,
    title: "Cache",
    question: "Is the cache saving me AeroDataBox calls?",
    detail: "Hit rate, misses, writes, storage size and every cached lookup with its expiry.",
  },
  {
    to: "/monitor/usage",
    icon: BarChart3,
    title: "API Usage",
    question: "Which tools does the agent use, and how well do they perform?",
    detail: "Calls per endpoint over time, p50/p95 latency, failures, plus model and speech activity.",
  },
  {
    to: "/monitor/heatmap",
    icon: Globe2,
    title: "Airport Heatmap",
    question: "Where are travellers going?",
    detail: "Top departure and destination airports and routes, derived from cached schedule lookups.",
  },
];

const SOURCES = [
  ["Function API calls", "App Insights requests (flights_search, flights_compare, flights_status)"],
  ["Agent / model / speech activity", "App Insights dependencies (execute_tool, chat, speech in/out)"],
  ["Cache hits and misses", "Table Storage response codes in App Insights traces (200 hit, 404 miss, 204 write)"],
  ["Cache contents and airports", "ApiCache table in the storage account, read-only"],
];

function Insight({ tone, children }) {
  const color = { good: "text-emerald-300", warn: "text-amber-300", bad: "text-rose-300", info: "text-sky-300" }[tone];
  return (
    <li className="flex gap-2 text-sm text-slate-300">
      <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-current ${color}`} />
      <span>{children}</span>
    </li>
  );
}

export default function MonitorOverview() {
  const usage = useMonitorData(monitorEndpoints.usage);
  const cache = useMonitorData(monitorEndpoints.cache);
  const { range } = useMonitorState();

  const tools = usage.data?.tools || [];
  const agent = usage.data?.agent || [];

  const totals = useMemo(() => {
    const calls = tools.reduce((s, t) => s + (t.calls || 0), 0);
    const failures = tools.reduce((s, t) => s + (t.failures || 0), 0);
    const weighted = tools.reduce((s, t) => s + (t.p50 || 0) * (t.calls || 0), 0);
    return { calls, failures, avg: calls ? Math.round(weighted / calls) : 0 };
  }, [tools]);

  const sum = (kind) => agent.filter((a) => a.kind === kind).reduce((s, a) => s + (a.calls || 0), 0);
  const turns = sum("model turn");
  const toolCalls = sum("tool call");
  const speechIn = sum("speech in");
  const speechOut = sum("speech out");

  const io = cache.data?.io;
  const state = cache.data?.state;
  const hitRate = io?.hit_rate;
  const errRate = totals.calls ? totals.failures / totals.calls : 0;
  const topTool = tools[0];
  const maxCalls = Math.max(1, ...tools.map((t) => t.calls || 0));
  const loading = usage.loading || cache.loading;

  const insights = [];
  if (!loading && !usage.error && !cache.error) {
    if (!totals.calls) insights.push(["info", "No Function API traffic in this range. Try a longer range in the sidebar."]);
    if (topTool) {
      insights.push([
        "info",
        <>
          Busiest endpoint is <b>{topTool.tool}</b> with {topTool.calls} calls (
          {Math.round((topTool.calls / Math.max(totals.calls, 1)) * 100)}% of traffic).
        </>,
      ]);
    }
    if (hitRate != null) {
      insights.push([
        hitRate >= 0.5 ? "good" : "warn",
        hitRate >= 0.5
          ? `Cache is answering ${Math.round(hitRate * 100)}% of lookups, which saves AeroDataBox quota.`
          : `Only ${Math.round(hitRate * 100)}% of lookups hit the cache. Most searches go to AeroDataBox; consider longer TTLs.`,
      ]);
    }
    if (totals.calls) {
      insights.push([
        errRate === 0 ? "good" : errRate < 0.05 ? "warn" : "bad",
        errRate === 0
          ? "No failed Function calls."
          : `${totals.failures} failed calls (${(errRate * 100).toFixed(1)}%). Check API Usage for the affected endpoint.`,
      ]);
    }
    if (state?.entries) {
      insights.push([
        state.warm === 0 ? "warn" : "info",
        `${state.warm} of ${state.entries} cache entries are still warm; ${state.expired} expired.`,
      ]);
    }
  }

  return (
    <div>
      <PageHeader
        icon={Gauge}
        title="Skyline Monitor"
        subtitle="Health of the voice travel agent backend at a glance"
        accent="amber"
        tip="Headline numbers for the selected time range, a plain-English summary, and a guide to the other pages. Use the sidebar to change the range."
      />

      <div className="mb-6 flex flex-wrap items-center gap-2 text-xs text-slate-400">
        <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-amber-300">
          Showing last {range}
        </span>
        <span className="rounded-full border border-slate-700 bg-slate-900/60 px-2.5 py-1">
          Agent: airline-and-travel-servicing
        </span>
        <span className="rounded-full border border-slate-700 bg-slate-900/60 px-2.5 py-1">
          Backend: skyline-api-13038
        </span>
      </div>

      {(usage.error || cache.error) && <ErrorCard message={usage.error || cache.error} />}

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-8 w-8 text-amber-400" />
        </div>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Metric label="API calls" value={totals.calls} accent="amber" hint="Function endpoints" />
            <Metric
              label="Cache hit rate"
              value={hitRate == null ? "—" : `${Math.round(hitRate * 100)}%`}
              accent="emerald"
              hint="Approximate"
            />
            <Metric label="Median latency" value={`${totals.avg} ms`} accent="brand" hint="Call-weighted p50" />
            <Metric
              label="Failures"
              value={totals.failures}
              accent={totals.failures ? "rose" : "emerald"}
              hint={totals.calls ? `${(errRate * 100).toFixed(1)}% error rate` : "No traffic"}
            />
          </div>

          <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ChartCard title="What the data says" tip="Auto-generated reading of the numbers for this time range.">
              {insights.length ? (
                <ul className="space-y-2">
                  {insights.map(([tone, text], i) => (
                    <Insight key={i} tone={tone}>
                      {text}
                    </Insight>
                  ))}
                </ul>
              ) : (
                <Empty text="Nothing to summarise yet." />
              )}
            </ChartCard>

            <ChartCard title="Traffic by endpoint" tip="Share of Function API calls per endpoint in this range.">
              {tools.length ? (
                <ul className="space-y-3">
                  {tools.map((t) => (
                    <li key={t.tool}>
                      <div className="mb-1 flex justify-between text-xs">
                        <span className="font-mono text-slate-300">{t.tool}</span>
                        <span className="text-slate-400">
                          {t.calls} calls · p50 {Math.round(t.p50 || 0)} ms
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-800">
                        <div
                          className="h-2 rounded-full bg-amber-400"
                          style={{ width: `${((t.calls || 0) / maxCalls) * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty />
              )}
            </ChartCard>
          </div>

          <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ChartCard
              title="Voice conversation activity"
              tip="Agent-side spans recorded by Foundry tracing. One conversation produces many model turns, tool calls and speech segments."
            >
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Metric label="Model turns" value={turns} accent="brand" />
                <Metric label="Tool calls" value={toolCalls} accent="amber" />
                <Metric label="Speech in" value={speechIn} />
                <Metric label="Speech out" value={speechOut} />
              </div>
              <p className="mt-3 flex items-start gap-1.5 text-xs text-slate-500">
                <Mic size={12} className="mt-0.5 shrink-0" />
                Agent tool calls can exceed Function calls when a call fails before reaching the API.
              </p>
            </ChartCard>

            <ChartCard title="Cache state" tip="Live contents of the ApiCache table.">
              <div className="grid grid-cols-3 gap-4 text-center">
                <Metric label="Entries" value={state?.entries ?? 0} />
                <Metric label="Warm" value={state?.warm ?? 0} accent="emerald" />
                <Metric label="Expired" value={state?.expired ?? 0} accent="amber" />
              </div>
              {Object.keys(state?.by_type || {}).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {Object.entries(state.by_type).map(([k, v]) => (
                    <span key={k} className="rounded-full bg-slate-900/70 px-2.5 py-1 text-xs text-slate-300">
                      {k}: <b className="text-amber-300">{v}</b>
                    </span>
                  ))}
                </div>
              )}
            </ChartCard>
          </div>
        </>
      )}

      <h2 className="mb-3 mt-8 text-sm font-semibold text-white">Where to go next</h2>
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        {GUIDE.map(({ to, icon: Icon, title, question, detail }) => (
          <Link key={to} to={to} className="group">
            <Card className="h-full transition group-hover:border-amber-500/40">
              <div className="mb-2 flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm font-semibold text-white">
                  <Icon size={16} className="text-amber-400" /> {title}
                </span>
                <ArrowRight
                  size={14}
                  className="text-slate-500 transition group-hover:translate-x-0.5 group-hover:text-amber-300"
                />
              </div>
              <p className="text-sm text-amber-200">{question}</p>
              <p className="mt-1 text-xs text-slate-400">{detail}</p>
            </Card>
          </Link>
        ))}
      </div>

      <Card>
        <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
          <Radar size={15} className="text-amber-400" /> Where the numbers come from
        </p>
        <ul className="space-y-1.5 text-xs text-slate-400">
          {SOURCES.map(([k, v]) => (
            <li key={k}>
              <span className="text-slate-200">{k}:</span> {v}
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-slate-500">
          Access is read-only. Cache hit rate and airport counts are estimates until the Function emits explicit cache
          events.
        </p>
      </Card>
    </div>
  );
}
