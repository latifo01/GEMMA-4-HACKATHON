import { AlertTriangle, ClipboardList, ExternalLink, ShieldAlert } from "lucide-react";

import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { formatDuration } from "../../lib/format";
import type { ApiMeta } from "../../types/api";
import type { TriageResultData } from "../../types/triage";

type TriageResultProps = {
  meta: ApiMeta | null;
  result: TriageResultData | null;
  isLoading: boolean;
};

const loadingSteps = [
  "Preparing case",
  "Retrieving IMCI guidance",
  "Running Gemma reasoning",
  "Applying safety checks",
  "Saving audit session",
];

const colorTone: Record<string, "green" | "amber" | "red" | "blue" | "neutral"> = {
  green: "green",
  yellow: "amber",
  red: "red",
};

export function TriageResult({ meta, result, isLoading }: TriageResultProps) {
  if (isLoading) {
    return (
      <section className="grid min-h-[420px] gap-4 rounded-md border border-slate-200 bg-white p-6 shadow-subtle">
        <div className="grid gap-2">
          <ClipboardList className="h-8 w-8 text-clinical-blue" aria-hidden="true" />
          <h2 className="text-lg font-bold text-ink">Running grounded triage</h2>
          <p className="text-sm leading-6 text-slate-600">
            Local optimistic steps are shown while the backend completes the non-streaming workflow.
          </p>
        </div>
        <ol className="grid content-start gap-2">
          {loadingSteps.map((step, index) => (
            <li key={step} className="flex items-center gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-blue-100 text-xs font-bold text-blue-700">
                {index + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="grid min-h-[420px] place-items-center rounded-md border border-slate-200 bg-white p-6 text-center shadow-subtle">
        <div className="grid max-w-md gap-3">
          <ClipboardList className="mx-auto h-8 w-8 text-slate-500" aria-hidden="true" />
          <h2 className="text-lg font-bold text-ink">Ready for triage</h2>
          <p className="text-sm leading-6 text-slate-600">
            Enter symptoms, optionally add audio or respiratory video, then run triage.
          </p>
        </div>
      </section>
    );
  }

  const tone = colorTone[result.triage_color?.toLowerCase()] ?? "blue";
  const sessionUrl = `/session/${encodeURIComponent(result.session_id)}`;

  return (
    <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-5 shadow-subtle">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={tone}>{result.triage_color}</Badge>
            <Badge tone={result.model.mode === "online" ? "blue" : "teal"}>
              {result.model.mode ?? "unknown"} · {result.model.name ?? "model"}
            </Badge>
            {meta?.duration_ms ? <Badge tone="neutral">{formatDuration(meta.duration_ms)}</Badge> : null}
          </div>
          <h2 className="text-xl font-bold tracking-normal text-ink">{result.classification}</h2>
        </div>
        <Button type="button" variant="ghost" onClick={() => window.location.assign(sessionUrl)}>
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
          Audit
        </Button>
      </div>

      <Alert tone="warning" className="flex gap-2">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>Clinical decision support only. Final decisions remain with qualified medical staff.</span>
      </Alert>

      <div className="grid gap-2">
        <h3 className="text-sm font-semibold text-slate-800">Recommended actions</h3>
        <ul className="grid gap-2">
          {result.recommendations.map((item) => (
            <li key={item} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm leading-6">
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="grid gap-2">
        <h3 className="text-sm font-semibold text-slate-800">Reasoning</h3>
        <p className="whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm leading-6">
          {result.translated_output || result.reasoning}
        </p>
      </div>

      {result.missing_information.length > 0 ? (
        <div className="grid gap-2">
          <h3 className="text-sm font-semibold text-slate-800">Missing information</h3>
          <div className="flex flex-wrap gap-2">
            {result.missing_information.map((item) => (
              <Badge key={item} tone="amber">
                {item}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      {result.safety_flags.length > 0 ? (
        <Alert tone="error" className="grid gap-2">
          <span className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            Safety flags
          </span>
          <span>{result.safety_flags.join(", ")}</span>
        </Alert>
      ) : null}

      <div className="grid gap-2">
        <h3 className="text-sm font-semibold text-slate-800">Citations</h3>
        <div className="grid gap-2">
          {result.citations.length > 0 ? (
            result.citations.slice(0, 5).map((citation, index) => (
              <div key={`${index}-${JSON.stringify(citation).slice(0, 24)}`} className="rounded-md border border-slate-200 px-3 py-2 text-xs leading-5 text-slate-700">
                {formatCitation(citation)}
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">No citation returned.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function formatCitation(citation: Record<string, unknown>) {
  const title = String(citation.title ?? citation.source ?? citation.document ?? "IMCI reference");
  const page = citation.page ? ` · page ${String(citation.page)}` : "";
  const excerpt = citation.text ?? citation.excerpt ?? citation.chunk;

  return excerpt ? `${title}${page}: ${String(excerpt).slice(0, 180)}` : `${title}${page}`;
}
