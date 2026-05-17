import { RefreshCw } from "lucide-react";
import { useState } from "react";

import { Button } from "../../components/ui/Button";
import type { TriageRequest, TriageResultData } from "../../types/triage";

type FieldConfig = {
  label: string;
  unit: string;
  min: number;
  max: number;
  step?: number;
  path: [keyof Pick<TriageRequest, "patient" | "measurements" | "context">, string];
};

const FIELD_CONFIG: Record<string, FieldConfig> = {
  "measurements.temperature_celsius": {
    label: "Temperature",
    unit: "°C",
    min: 35,
    max: 42,
    step: 0.1,
    path: ["measurements", "temperature_celsius"],
  },
  "context.fever_duration_days": {
    label: "Fever duration",
    unit: "days",
    min: 0,
    max: 30,
    path: ["context", "fever_duration_days"],
  },
  "patient.age_months": {
    label: "Child age",
    unit: "months",
    min: 0,
    max: 216,
    path: ["patient", "age_months"],
  },
  "measurements.respiratory_rate_bpm": {
    label: "Respiratory rate",
    unit: "bpm",
    min: 0,
    max: 120,
    path: ["measurements", "respiratory_rate_bpm"],
  },
  "respiratory_rate_bpm": {
    label: "Respiratory rate",
    unit: "bpm",
    min: 0,
    max: 120,
    path: ["measurements", "respiratory_rate_bpm"],
  },
  "measurements.weight_kg": {
    label: "Weight",
    unit: "kg",
    min: 0,
    max: 30,
    step: 0.1,
    path: ["measurements", "weight_kg"],
  },
};

interface Props {
  result: TriageResultData;
  lastRequest: TriageRequest;
  onRefine: (enrichedRequest: TriageRequest) => void;
  isDisabled?: boolean;
}

export function RefineDiagnosisPanel({ result, lastRequest, onRefine, isDisabled }: Props) {
  const knownFields = result.missing_information.filter((f) => f in FIELD_CONFIG);
  const [values, setValues] = useState<Record<string, string>>({});

  if (knownFields.length === 0) return null;

  const hasAnyValue = knownFields.some((f) => values[f] !== undefined && values[f] !== "");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hasAnyValue) return;

    let patient = { ...(lastRequest.patient as Record<string, unknown>) };
    let measurements = { ...(lastRequest.measurements as Record<string, unknown>) };
    let context = { ...(lastRequest.context as Record<string, unknown>) };

    for (const field of knownFields) {
      const raw = values[field];
      if (raw === undefined || raw === "") continue;
      const num = parseFloat(raw);
      if (isNaN(num)) continue;
      const [topKey, subKey] = FIELD_CONFIG[field].path;
      if (topKey === "patient") patient = { ...patient, [subKey]: num };
      else if (topKey === "measurements") measurements = { ...measurements, [subKey]: num };
      else if (topKey === "context") context = { ...context, [subKey]: num };
    }

    onRefine({
      ...lastRequest,
      session_id: result.session_id,
      patient,
      measurements,
      context,
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-4"
    >
      <p className="text-sm font-semibold text-amber-900">Complete the assessment</p>
      <p className="mt-0.5 text-xs leading-5 text-amber-700">
        Providing the missing values will allow a more precise diagnosis.
      </p>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {knownFields.map((field) => {
          const cfg = FIELD_CONFIG[field];
          return (
            <div
              key={field}
              className="grid grid-cols-[1fr_auto] items-center rounded-md border border-amber-300 bg-white focus-within:border-amber-500 focus-within:ring-2 focus-within:ring-amber-100"
            >
              <div className="flex flex-col px-3 py-1.5">
                <span className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
                  {cfg.label}
                </span>
                <input
                  type="number"
                  min={cfg.min}
                  max={cfg.max}
                  step={cfg.step ?? 1}
                  placeholder={`${cfg.min}–${cfg.max}`}
                  value={values[field] ?? ""}
                  onChange={(e) =>
                    setValues((v) => ({ ...v, [field]: e.target.value }))
                  }
                  className="text-sm text-ink outline-none"
                />
              </div>
              <span className="border-l border-amber-200 px-3 text-sm text-slate-500">
                {cfg.unit}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-3 flex justify-end">
        <Button
          type="submit"
          variant="primary"
          disabled={isDisabled || !hasAnyValue}
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Refine diagnosis
        </Button>
      </div>
    </form>
  );
}
