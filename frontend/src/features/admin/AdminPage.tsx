import { useMutation, useQuery } from "@tanstack/react-query";
import { Button, Card, Spinner } from "../../components/ui";
import { api } from "../../lib/api-client";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-800">{value}</p>
    </Card>
  );
}

export function AdminPage() {
  const analytics = useQuery({ queryKey: ["analytics"], queryFn: api.analytics });
  const queue = useQuery({ queryKey: ["queue"], queryFn: api.queueMonitor });
  const providers = useQuery({ queryKey: ["providers"], queryFn: api.activeProviders });
  const evalRun = useMutation({ mutationFn: api.runEval });

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <h1 className="text-lg font-semibold text-slate-800">Admin &amp; Analytics</h1>

      {analytics.isLoading ? (
        <Spinner />
      ) : (
        analytics.data && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Conversations" value={analytics.data.conversations} />
            <Stat label="Messages" value={analytics.data.messages} />
            <Stat label="Tokens out" value={analytics.data.tokens_out} />
            <Stat label="Latency p95 (ms)" value={analytics.data.latency_p95_ms} />
            <Stat label="👍" value={analytics.data.feedback_up} />
            <Stat label="👎" value={analytics.data.feedback_down} />
          </div>
        )
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Cost by provider</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400">
                <th className="py-1">Provider</th>
                <th>Tokens</th>
                <th>Cost (USD)</th>
              </tr>
            </thead>
            <tbody>
              {(analytics.data?.cost_by_provider ?? []).map((c) => (
                <tr key={c.provider} className="border-t border-slate-100">
                  <td className="py-1">{c.provider}</td>
                  <td>{c.tokens_in + c.tokens_out}</td>
                  <td>${c.cost_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card className="p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Ingestion queue</h2>
          <div className="flex flex-wrap gap-2 text-sm">
            {Object.entries(queue.data?.by_status ?? {}).map(([k, v]) => (
              <span key={k} className="rounded bg-slate-100 px-2 py-1">
                {k}: <strong>{v}</strong>
              </span>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Top retrieved documents</h2>
          <ul className="space-y-1 text-sm">
            {(analytics.data?.top_documents ?? []).map((d) => (
              <li key={d.document_id} className="flex justify-between">
                <span className="truncate text-slate-700">{d.filename ?? d.document_id}</span>
                <span className="text-slate-400">{d.retrievals}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Active providers</h2>
          <div className="grid grid-cols-2 gap-1 text-sm">
            {Object.entries(providers.data ?? {}).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-slate-500">{k}</span>
                <span className="font-medium text-slate-700">{v}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">RAG evaluation</h2>
          <Button onClick={() => evalRun.mutate()} disabled={evalRun.isPending}>
            {evalRun.isPending ? "Running…" : "Run eval"}
          </Button>
        </div>
        {evalRun.data && (
          <div>
            <p className="mb-2 text-sm">
              Scorecard ({evalRun.data.cases} cases, {evalRun.data.harness}):{" "}
              <span className={evalRun.data.passed ? "text-green-600" : "text-red-600"}>
                {evalRun.data.passed ? "PASS" : "FAIL"}
              </span>{" "}
              <span className="text-slate-400">(threshold {evalRun.data.threshold})</span>
            </p>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              {evalRun.data.metrics.map((m) => (
                <div key={m.name} className="rounded border border-slate-100 p-2 text-sm">
                  <p className="text-slate-500">{m.name}</p>
                  <p className={m.passed ? "text-green-600" : "text-red-600"}>
                    {m.score.toFixed(3)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
