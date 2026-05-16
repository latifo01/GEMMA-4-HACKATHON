import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, History } from "lucide-react";

import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Spinner } from "../components/ui/Spinner";
import { formatDateTime } from "../lib/format";
import { getSession } from "../services/api/sessions";

type SessionPageProps = {
  sessionId: string;
};

export function SessionPage({ sessionId }: SessionPageProps) {
  const session = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => getSession(sessionId),
  });

  return (
    <div className="grid gap-4">
      <Button type="button" variant="ghost" className="w-fit" onClick={() => window.location.assign("/")}>
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back
      </Button>

      <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-5 shadow-subtle">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="grid gap-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
              <History className="h-4 w-4" aria-hidden="true" />
              Audit session
            </div>
            <h2 className="break-all text-xl font-bold text-ink">{sessionId}</h2>
          </div>
          {session.data ? (
            <Badge tone={session.data.data.status === "completed" ? "green" : "amber"}>
              {session.data.data.status}
            </Badge>
          ) : null}
        </div>

        {session.isLoading ? <Spinner label="Loading session" /> : null}
        {session.isError ? <Alert tone="error">Unable to load this session.</Alert> : null}

        {session.data ? (
          <div className="grid gap-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <Metric label="Created" value={formatDateTime(session.data.data.created_at)} />
              <Metric label="Updated" value={formatDateTime(session.data.data.updated_at)} />
              <Metric label="Model mode" value={session.data.data.model_mode ?? "unavailable"} />
            </div>
            <JsonPanel title="Request" value={session.data.data.request} />
            {session.data.data.result ? <JsonPanel title="Result" value={session.data.data.result} /> : null}
            {session.data.data.errors.length > 0 ? <JsonPanel title="Errors" value={session.data.data.errors} /> : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="text-xs font-semibold uppercase text-slate-500">{label}</div>
      <div className="mt-1 break-words text-sm font-semibold text-ink">{value}</div>
    </div>
  );
}

function JsonPanel({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="grid gap-2">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <pre className="max-h-[460px] overflow-auto rounded-md border border-slate-200 bg-slate-950 p-4 text-xs leading-5 text-slate-100">
        {JSON.stringify(value, null, 2)}
      </pre>
    </section>
  );
}
