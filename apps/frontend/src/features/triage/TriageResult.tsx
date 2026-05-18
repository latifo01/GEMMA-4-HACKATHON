import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  FileText,
  Loader2,
  ShieldAlert,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import { useEffect, useState } from "react";

import { env } from "../../app/env";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { formatDuration } from "../../lib/format";
import type { ApiMeta } from "../../types/api";
import type { TriageRequest, TriageResultData } from "../../types/triage";
import { RefineDiagnosisPanel } from "./RefineDiagnosisPanel";
import type { NodeStatus, StreamNode } from "./useTriageStream";

type TriageResultProps = {
  meta: ApiMeta | null;
  result: TriageResultData | null;
  isLoading: boolean;
  streamNodes?: Record<StreamNode, NodeStatus>;
  lastRequest?: TriageRequest | null;
  onRefine?: (enrichedRequest: TriageRequest) => void;
};

type Tone = "green" | "amber" | "red" | "blue" | "neutral";

const NODE_LABELS: Record<StreamNode, string> = {
  intake: "Case intake",
  symptom_extraction: "Gemma 4 signal extraction",
  rag_retrieval: "IMCI evidence search",
  imci_reasoning: "Safety tool reasoning",
  verification: "Danger sign check",
  translation: "Caregiver language output",
};

const colorTone: Record<string, Tone> = {
  green: "green",
  yellow: "amber",
  pink: "red",
  red: "red",
};

const accentStyle: Record<string, string> = {
  pink: "border-red-300 bg-white shadow-red-100",
  red: "border-red-300 bg-white shadow-red-100",
  yellow: "border-amber-300 bg-white shadow-amber-100",
  green: "border-green-300 bg-white shadow-green-100",
};

const decisionStyle: Record<string, string> = {
  pink: "border-red-200 bg-red-50 text-red-950",
  red: "border-red-200 bg-red-50 text-red-950",
  yellow: "border-amber-200 bg-amber-50 text-amber-950",
  green: "border-green-200 bg-green-50 text-green-950",
};

export function TriageResult({ meta, result, isLoading, streamNodes, lastRequest, onRefine }: TriageResultProps) {
  const elapsedSeconds = useElapsedSeconds(isLoading);

  if (isLoading) {
    return (
      <section className="grid min-h-[420px] gap-5 rounded-md border border-slate-200 bg-white p-6 shadow-subtle">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="grid gap-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-700">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              Gemma 4 clinical pipeline
            </div>
            <h2 className="text-xl font-bold text-ink">Reading the case</h2>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              The backend is streaming each reasoning step as it extracts signals, searches IMCI evidence,
              and applies deterministic safety checks.
            </p>
          </div>
          <Badge tone="neutral">{elapsedSeconds}s</Badge>
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
            Enter symptoms, use the microphone, or add media, then run the Gemma 4 triage workflow.
          </p>
        </div>
      </section>
    );
  }

  const colorKey = result.triage_color?.toLowerCase() ?? "neutral";
  const tone = colorTone[colorKey] ?? "blue";
  const sectionClass = accentStyle[colorKey] ?? "border-slate-200 bg-white";
  const decisionClass = decisionStyle[colorKey] ?? "border-slate-200 bg-slate-50 text-slate-950";
  const isPulse = colorKey === "pink" || colorKey === "red";
  const sessionUrl = `/session/${encodeURIComponent(result.session_id)}`;
  const positiveSignals = getPositiveSignals(result.extracted_symptoms);
  const toolNames = result.tool_results.map((tool) => String(tool.tool_name ?? tool.name ?? "clinical_tool"));
  const clinicalReasoning = formatClinicalText(result.reasoning);
  const caregiverExplanation = formatClinicalText(result.translated_output || "");
  const showCaregiverExplanation = caregiverExplanation.length > 0 && caregiverExplanation !== clinicalReasoning;
  const isRTL = /[\u0600-\u06FF]/.test(caregiverExplanation.slice(0, 30));

  return (
    <section className={`grid gap-5 rounded-md border p-5 shadow-subtle ${sectionClass}`}>
      <div className={`grid gap-4 rounded-md border p-4 ${decisionClass}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="grid gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={tone} className={isPulse ? "animate-pulse" : undefined}>
                {result.triage_color}
              </Badge>
              <Badge tone={result.model.mode === "online" ? "blue" : "teal"}>
                Gemma 4 {result.model.mode ?? "route"}
              </Badge>
              {meta?.duration_ms ? <Badge tone="neutral">{formatDuration(meta.duration_ms)}</Badge> : null}
            </div>
            <div className="flex items-start gap-3">
              <Stethoscope className="mt-1 h-5 w-5 shrink-0" aria-hidden="true" />
              <div>
                <h2 className="text-2xl font-bold leading-tight text-ink">{formatLabel(result.classification)}</h2>
                <p className="mt-1 text-sm font-semibold">{getSeverityLabel(result.triage_color)}</p>
              </div>
            </div>
          </div>
          <Button type="button" variant="secondary" onClick={() => window.location.assign(sessionUrl)}>
            <ExternalLink className="h-4 w-4" aria-hidden="true" />
            Audit
          </Button>
        </div>

        <Alert tone="warning" className="flex gap-2 bg-white/70">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Clinical decision support only. Final decisions remain with qualified medical staff.</span>
        </Alert>
      </div>

      <section className="grid gap-3">
        <h3 className="text-sm font-semibold text-slate-900">Next actions</h3>
        <ol className="grid gap-2">
          {result.recommendations.map((item, index) => (
            <li key={`${index}-${item}`} className="grid grid-cols-[2rem_1fr] gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-white text-sm font-bold text-slate-700">
                {index + 1}
              </span>
              <span className="self-center text-sm leading-6 text-slate-900">{item}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-3 rounded-md border border-blue-100 bg-blue-50/50 p-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-blue-700" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-slate-900">Gemma 4 synthesis</h3>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <SummaryTile label="Model route" value={formatModelName(result.model.name)} tone="blue" />
          <SummaryTile label="Evidence" value={`${result.citations.length} IMCI source${result.citations.length === 1 ? "" : "s"}`} tone="green" />
          <SummaryTile label="Safety layer" value={`${toolNames.length || 1} deterministic check${toolNames.length === 1 ? "" : "s"}`} tone="amber" />
        </div>
        <div className="grid gap-2">
          <h4 className="text-xs font-semibold uppercase text-slate-500">Signals detected</h4>
          {positiveSignals.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {positiveSignals.slice(0, 8).map((signal) => (
                <Badge key={signal} tone="blue">
                  {formatLabel(signal)}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-600">No structured clinical signal was returned.</p>
          )}
        </div>
        {toolNames.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {toolNames.map((toolName) => (
              <Badge key={toolName} tone="teal">
                {formatLabel(toolName)}
              </Badge>
            ))}
          </div>
        ) : null}
      </section>

      <section className="grid gap-3">
        <h3 className="text-sm font-semibold text-slate-900">Why this decision</h3>
        <ReasoningTrace reasoning={clinicalReasoning} />
        {showCaregiverExplanation ? (
          <div className="grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-3">
            <h4 className="text-xs font-semibold uppercase text-slate-500">Caregiver wording</h4>
            <p dir={isRTL ? "rtl" : "ltr"} className="whitespace-pre-wrap text-sm leading-6 text-slate-800">
              {caregiverExplanation}
            </p>
          </div>
        ) : null}
      </section>

      {result.missing_information.length > 0 ? (
        <section className="grid gap-2">
          <h3 className="text-sm font-semibold text-slate-900">Missing information</h3>
          <div className="flex flex-wrap gap-2">
            {result.missing_information.map((item) => (
              <Badge key={item} tone="amber">
                {formatLabel(item)}
              </Badge>
            ))}
          </div>
        </section>
      ) : null}

      {lastRequest && onRefine ? (
        <RefineDiagnosisPanel
          result={result}
          lastRequest={lastRequest}
          onRefine={onRefine}
          isDisabled={isLoading}
        />
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

      <EvidencePanel citations={result.citations} />
    </section>
  );
}

function ReasoningTrace({ reasoning }: { reasoning: string }) {
  const lines = reasoning.split("\n").map((line) => line.trim()).filter(Boolean);

  return (
    <ol className="grid gap-2">
      {lines.map((line, index) => (
        <li key={`${index}-${line.slice(0, 24)}`} className="grid gap-2 rounded-md border border-slate-200 bg-white px-3 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={reasoningTone(line)}>{reasoningLabel(line)}</Badge>
            <span className="text-xs font-semibold uppercase text-slate-400">Step {index + 1}</span>
          </div>
          <p className="text-sm leading-6 text-slate-800">{line}</p>
        </li>
      ))}
    </ol>
  );
}

function StreamingTrace({ nodes }: { nodes?: Record<string, NodeStatus> }) {
  return (
    <ol className="grid content-start gap-2">
      {(Object.entries(NODE_LABELS) as [StreamNode, string][]).map(([node, label], index) => {
        const status: NodeStatus = nodes?.[node] ?? "pending";
        const stateClass = {
          pending: "bg-slate-50 border-slate-200 text-slate-400",
          running: "bg-blue-50 border-blue-300 text-blue-800",
          completed: "bg-green-50 border-green-300 text-green-800",
        }[status];
        return (
          <li
            key={node}
            className={`flex items-center gap-3 rounded-md border px-3 py-2 text-sm transition-all duration-300 ${stateClass}`}
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-bold">
              {status === "completed" ? (
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              ) : status === "running" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                index + 1
              )}
            </span>
            <span>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

function reasoningLabel(line: string) {
  if (line.startsWith("Gemma 4 extracted")) return "Signals";
  if (line.startsWith("Safety override")) return "Safety override";
  if (line.includes("rule:")) return "IMCI rule";
  if (line.startsWith("Open uncertainty")) return "Uncertainty";
  if (line.startsWith("Evidence used")) return "Evidence";
  return "Decision";
}

function reasoningTone(line: string): Tone {
  if (line.startsWith("Gemma 4 extracted")) return "blue";
  if (line.startsWith("Safety override")) return "red";
  if (line.includes("rule:")) return "amber";
  if (line.startsWith("Open uncertainty")) return "amber";
  if (line.startsWith("Evidence used")) return "green";
  return "neutral";
}

function EvidencePanel({ citations }: { citations: Array<Record<string, unknown>> }) {
  return (
    <section className="grid gap-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-slate-600" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-slate-900">IMCI evidence</h3>
        </div>
        <Badge tone="neutral">{citations.length} cited</Badge>
      </div>
      <div className="grid gap-2">
        {citations.length > 0 ? (
          citations.slice(0, 4).map((citation, index) => (
            <CitationCard key={`${index}-${JSON.stringify(citation).slice(0, 24)}`} citation={citation} />
          ))
        ) : (
          <p className="text-sm text-slate-500">No citation returned.</p>
        )}
      </div>
    </section>
  );
}

function CitationCard({ citation }: { citation: Record<string, unknown> }) {
  const title = String(citation.title ?? citation.source ?? "IMCI reference");
  const page = citation.page ? `page ${String(citation.page)}` : "";
  const excerpt = String(citation.text ?? citation.excerpt ?? citation.quote ?? "");
  const imageUrl = citation.image_url ? resolveImageUrl(String(citation.image_url)) : null;
  const score = typeof citation.relevance_score === "number" ? citation.relevance_score : null;

  return (
    <article className="grid overflow-hidden rounded-md border border-slate-200 bg-white text-xs leading-5 text-slate-700 sm:grid-cols-[128px_1fr]">
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={`IMCI ${page || "page"}`}
          className="h-32 w-full border-b border-slate-200 object-cover object-top sm:border-b-0 sm:border-r"
        />
      ) : null}
      <div className="grid gap-2 px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-slate-900">{title}</span>
          {page ? <Badge tone="neutral">{page}</Badge> : null}
        </div>
        {score !== null ? (
          <div className="flex items-center gap-2">
            <div className="h-1 flex-1 rounded bg-slate-200">
              <div
                className={`h-1 rounded transition-all duration-500 ${score >= 0.6 ? "bg-green-400" : score >= 0.35 ? "bg-amber-400" : "bg-rose-400"}`}
                style={{ width: `${Math.round(score * 100)}%` }}
              />
            </div>
            <span className="text-slate-500">{Math.round(score * 100)}%</span>
          </div>
        ) : null}
        {excerpt ? <p className="line-clamp-3 text-slate-600">{excerpt.slice(0, 220)}</p> : null}
      </div>
    </article>
  );
}

function SummaryTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: Tone;
}) {
  const toneClass = {
    green: "border-green-200 bg-white text-green-900",
    amber: "border-amber-200 bg-white text-amber-900",
    red: "border-red-200 bg-white text-red-900",
    blue: "border-blue-200 bg-white text-blue-900",
    neutral: "border-slate-200 bg-white text-slate-900",
  }[tone];

  return (
    <div className={`rounded-md border px-3 py-2 ${toneClass}`}>
      <div className="text-xs font-semibold uppercase opacity-70">{label}</div>
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

function getPositiveSignals(symptoms: Record<string, unknown>) {
  return Object.entries(symptoms)
    .filter(([key, value]) => key !== "modules" && (value === true || (typeof value === "string" && value.length > 0)))
    .map(([key]) => key);
}

function getSeverityLabel(triageColor: string) {
  const normalized = triageColor.toLowerCase();
  if (normalized === "pink" || normalized === "red") {
    return "Urgent referral or immediate clinical review";
  }
  if (normalized === "yellow") {
    return "Same-day clinical assessment";
  }
  if (normalized === "green") {
    return "Lower-risk guidance with return precautions";
  }
  return "Clinician assessment required";
}

function formatModelName(value: unknown) {
  if (!value) {
    return "Gemma 4";
  }
  return String(value).replace(/^models\//, "");
}

function resolveImageUrl(imageUrl: string) {
  if (imageUrl.startsWith("http://") || imageUrl.startsWith("https://")) {
    return imageUrl;
  }
  return `${env.apiBaseUrl}${imageUrl}`;
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
