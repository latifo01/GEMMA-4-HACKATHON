import { AlertTriangle, ClipboardList, ExternalLink, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { env } from "../../app/env";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { formatDuration } from "../../lib/format";
import type { ApiMeta } from "../../types/api";
import type { TriageRequest, TriageResultData } from "../../types/triage";
import type { NodeStatus, StreamNode } from "./useTriageStream";
import { RefineDiagnosisPanel } from "./RefineDiagnosisPanel";

type TriageResultProps = {
  meta: ApiMeta | null;
  result: TriageResultData | null;
  isLoading: boolean;
  streamNodes?: Record<StreamNode, NodeStatus>;
  lastRequest?: TriageRequest | null;
  onRefine?: (enrichedRequest: TriageRequest) => void;
};

const NODE_LABELS: Record<StreamNode, string> = {
  intake: "Validating patient data",
  symptom_extraction: "Extracting clinical signals (Gemma 4)",
  rag_retrieval: "Searching IMCI guidelines",
  imci_reasoning: "Running deterministic safety tools",
  verification: "Checking danger signs",
  translation: "Generating multilingual output",
};

const colorTone: Record<string, "green" | "amber" | "red" | "blue" | "neutral"> = {
  green: "green",
  yellow: "amber",
  pink: "red",
  red: "red",
};

const sectionStyle: Record<string, string> = {
  pink: "border-red-400 bg-red-50",
  red: "border-red-400 bg-red-50",
  yellow: "border-amber-400 bg-amber-50",
  green: "border-green-400 bg-green-50",
};

export function TriageResult({ meta, result, isLoading, streamNodes, lastRequest, onRefine }: TriageResultProps) {
  const elapsedSeconds = useElapsedSeconds(isLoading);

  if (isLoading) {
    return (
      <section className="grid min-h-[420px] gap-4 rounded-md border border-slate-200 bg-white p-6 shadow-subtle">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <ClipboardList className="h-8 w-8 text-clinical-blue" aria-hidden="true" />
            <Badge tone="neutral">{elapsedSeconds}s</Badge>
          </div>
          <h2 className="text-lg font-bold text-ink">Running Gemma 4 triage</h2>
          <p className="text-sm leading-6 text-slate-600">
            The backend is extracting symptoms, grounding the case, and applying deterministic safety tools.
          </p>
        </div>
        <StreamingTrace nodes={streamNodes} />
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

  const colorKey = result.triage_color?.toLowerCase() ?? "neutral";
  const tone = colorTone[colorKey] ?? "blue";
  const sectionClass = sectionStyle[colorKey] ?? "border-slate-200 bg-white";
  const isPulse = colorKey === "pink" || colorKey === "red";
  const sessionUrl = `/session/${encodeURIComponent(result.session_id)}`;
  const evidenceCount = result.citations.length;
  const toolNames = result.tool_results.map((tool) => String(tool.tool_name ?? tool.name ?? "clinical_tool"));

  const isRTL =
    result.translated_output != null &&
    result.translated_output.length > 0 &&
    /[؀-ۿ]/.test(result.translated_output.slice(0, 30));

  return (
    <section
      className={`grid gap-4 rounded-md border p-5 shadow-subtle transition-colors duration-500 ${sectionClass}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={tone} className={isPulse ? "animate-pulse" : undefined}>
              {result.triage_color}
            </Badge>
            <Badge tone={result.model.mode === "online" ? "blue" : "teal"}>
              {result.model.mode ?? "unknown"} · {result.model.name ?? "model"}
            </Badge>
            {meta?.duration_ms ? <Badge tone="neutral">{formatDuration(meta.duration_ms)}</Badge> : null}
          </div>
          <h2 className="text-xl font-bold tracking-normal text-ink">{formatLabel(result.classification)}</h2>
          <p className="text-sm font-semibold text-slate-700">{getSeverityLabel(result.triage_color)}</p>
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

      <div className="grid gap-2 sm:grid-cols-3">
        <SummaryTile label="Urgency" value={getSeverityLabel(result.triage_color)} tone={tone} />
        <SummaryTile label="Evidence" value={`${evidenceCount} IMCI citation${evidenceCount === 1 ? "" : "s"}`} tone="green" />
        <SummaryTile label="Audit" value={shortSessionId(result.session_id)} tone="neutral" />
      </div>

      <div className="grid gap-2">
        <h3 className="text-sm font-semibold text-slate-800">Recommended actions</h3>
        <ul className="grid gap-2">
          {result.recommendations.map((item) => (
            <li key={item} className="rounded-md border border-slate-200 bg-white/60 px-3 py-2 text-sm leading-6">
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="grid gap-2">
        <h3 className="text-sm font-semibold text-slate-800">Reasoning</h3>
        <p
          dir={isRTL ? "rtl" : "ltr"}
          className="whitespace-pre-wrap rounded-md border border-slate-200 bg-white/60 px-3 py-2 text-sm leading-6"
        >
          {formatClinicalText(result.translated_output || result.reasoning)}
        </p>
      </div>

      {toolNames.length > 0 ? (
        <div className="grid gap-2">
          <h3 className="text-sm font-semibold text-slate-800">Clinical trace</h3>
          <div className="flex flex-wrap gap-2">
            {toolNames.map((toolName) => (
              <Badge key={toolName} tone="blue">
                {formatLabel(toolName)}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      {result.missing_information.length > 0 ? (
        <div className="grid gap-2">
          <h3 className="text-sm font-semibold text-slate-800">Missing information</h3>
          <div className="flex flex-wrap gap-2">
            {result.missing_information.map((item) => (
              <Badge key={item} tone="amber">
                {formatLabel(item)}
              </Badge>
            ))}
          </div>
          {lastRequest && onRefine ? (
            <RefineDiagnosisPanel
              result={result}
              lastRequest={lastRequest}
              onRefine={onRefine}
              isDisabled={isLoading}
            />
          ) : null}
        </div>
      ) : null}

      {result.safety_flags.length > 0 ? (
        <Alert tone="error" className="grid gap-2">
          <span className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            Safety flags
          </span>
          <span>{result.safety_flags.map(formatLabel).join(", ")}</span>
        </Alert>
      ) : null}

      <div className="grid gap-2">
        <h3 className="text-sm font-semibold text-slate-800">Citations</h3>
        <div className="grid gap-2">
          {result.citations.length > 0 ? (
            result.citations.slice(0, 5).map((citation, index) => (
              <CitationCard key={`${index}-${JSON.stringify(citation).slice(0, 24)}`} citation={citation} />
            ))
          ) : (
            <p className="text-sm text-slate-500">No citation returned.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function StreamingTrace({ nodes }: { nodes?: Record<string, NodeStatus> }) {
  return (
    <ol className="grid content-start gap-2">
      {(Object.entries(NODE_LABELS) as [StreamNode, string][]).map(([node, label], index) => {
        const status: NodeStatus = nodes?.[node] ?? "pending";
        const stateClass = {
          pending: "bg-slate-50 border-slate-200 text-slate-400",
          running: "bg-blue-50 border-blue-300 text-blue-800 animate-pulse",
          completed: "bg-green-50 border-green-300 text-green-800",
        }[status];
        const icon = status === "completed" ? "✓" : status === "running" ? "◎" : String(index + 1);
        return (
          <li
            key={node}
            className={`flex items-center gap-3 rounded-md border px-3 py-2 text-sm transition-all duration-300 ${stateClass}`}
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-bold">
              {icon}
            </span>
            <span>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

function CitationCard({ citation }: { citation: Record<string, unknown> }) {
  const title = String(citation.title ?? citation.source ?? "IMCI reference");
  const page = citation.page ? ` · page ${String(citation.page)}` : "";
  const excerpt = String(citation.text ?? citation.excerpt ?? citation.quote ?? "");
  const imageUrl = citation.image_url
    ? `${env.apiBaseUrl}${String(citation.image_url)}`
    : null;
  const score = typeof citation.relevance_score === "number" ? citation.relevance_score : null;

  return (
    <div className="overflow-hidden rounded-md border border-slate-200 text-xs leading-5 text-slate-700">
      {imageUrl && (
        <img
          src={imageUrl}
          alt={`IMCI page ${String(citation.page ?? "")}`}
          className="max-h-36 w-full border-b border-slate-200 object-cover object-top"
        />
      )}
      <div className="px-3 py-2">
        <span className="font-semibold">
          {title}
          {page}
        </span>
        {score !== null && (
          <div className="mt-1.5 flex items-center gap-2">
            <div className="h-1 flex-1 rounded bg-slate-200">
              <div
                className={`h-1 rounded transition-all duration-500 ${score >= 0.6 ? "bg-green-400" : score >= 0.35 ? "bg-amber-400" : "bg-rose-400"}`}
                style={{ width: `${Math.round(score * 100)}%` }}
              />
            </div>
            <span className="text-slate-400">{Math.round(score * 100)}%</span>
          </div>
        )}
        {excerpt && <p className="mt-1">{excerpt.slice(0, 180)}</p>}
      </div>
    </div>
  );
}

function SummaryTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "green" | "amber" | "red" | "blue" | "neutral";
}) {
  const toneClass = {
    green: "border-green-200 bg-green-50 text-green-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    red: "border-red-200 bg-red-50 text-red-900",
    blue: "border-blue-200 bg-blue-50 text-blue-900",
    neutral: "border-slate-200 bg-slate-50 text-slate-900",
  }[tone];

  return (
    <div className={`rounded-md border px-3 py-2 ${toneClass}`}>
      <div className="text-xs font-semibold uppercase tracking-normal opacity-75">{label}</div>
      <div className="mt-1 text-sm font-bold leading-5">{value}</div>
    </div>
  );
}

function useElapsedSeconds(isLoading: boolean) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      setElapsedSeconds(0);
      return;
    }

    const startedAt = Date.now();
    const interval = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);

    return () => window.clearInterval(interval);
  }, [isLoading]);

  return elapsedSeconds;
}

function getSeverityLabel(triageColor: string) {
  const normalized = triageColor.toLowerCase();
  if (normalized === "pink" || normalized === "red") {
    return "Urgent clinical review";
  }
  if (normalized === "yellow") {
    return "Same-day assessment";
  }
  if (normalized === "green") {
    return "Lower-risk guidance";
  }
  return "Clinician assessment";
}

function shortSessionId(sessionId: string) {
  return sessionId.length > 10 ? `${sessionId.slice(0, 8)}...` : sessionId;
}

function formatClinicalText(text: string) {
  return text.replace(/\b[A-Z][A-Z0-9_]{2,}\b/g, (value) => formatLabel(value));
}

function formatLabel(value: string) {
  if (value === "IMCI" || value === "RAG") {
    return value;
  }

  return value
    .replace(/^measurements\./, "")
    .replace(/^context\./, "")
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
