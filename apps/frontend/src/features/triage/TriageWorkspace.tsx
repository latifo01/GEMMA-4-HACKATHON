import { zodResolver } from "@hookform/resolvers/zod";
import { ClipboardCheck, PlayCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LanguageSelector } from "../../components/shared/LanguageSelector";
import { ModeSelector } from "../../components/shared/ModeSelector";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { Spinner } from "../../components/ui/Spinner";
import { useBackendHealth } from "../health/useBackendHealth";
import { AudioUpload } from "../audio/AudioUpload";
import { useAudioTranscription } from "../audio/useAudioTranscription";
import { useVideoAnalysis } from "../video/useVideoAnalysis";
import { VideoUpload } from "../video/VideoUpload";
import { getErrorMessage } from "../../lib/errors";
import type { TriageRequest } from "../../types/triage";
import { TriageResult } from "./TriageResult";
import { useTriageStream } from "./useTriageStream";

const triageSchema = z.object({
  transcript: z.string().min(8, "Enter at least a short symptom description."),
  source_language: z.enum(["auto", "en", "fr", "ar-SD"]),
  target_language: z.enum(["en", "fr", "ar-SD"]),
  model_mode: z.enum(["auto", "online", "offline"]),
  age_months: z.number().int().min(0, "Age cannot be negative.").max(216, "Age should be 216 months or less."),
  respiratory_rate_bpm: z.number().min(0).max(120).optional(),
});

export type TriageFormValues = z.infer<typeof triageSchema>;

const demoCases = [
  {
    label: "Sample",
    transcript: "Mother says the 18-month-old child has cough and fast breathing. The child can drink.",
    source_language: "en",
    respiratory_rate_bpm: 48,
  },
  {
    label: "Danger sign",
    transcript: "L'enfant presente une forte fievre, vomit plusieurs fois et refuse de boire.",
    source_language: "fr",
    respiratory_rate_bpm: undefined,
  },
  {
    label: "Dehydration",
    transcript: "The child has diarrhea, sunken eyes, is restless, and drinks eagerly.",
    source_language: "en",
    respiratory_rate_bpm: undefined,
  },
] as const;

export function TriageWorkspace() {
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<TriageRequest | null>(null);

  const health = useBackendHealth();
  const audioMutation = useAudioTranscription();
  const videoMutation = useVideoAnalysis();
  const triageStream = useTriageStream();

  const {
    formState: { errors },
    handleSubmit,
    register,
    setValue,
    watch,
  } = useForm<TriageFormValues>({
    resolver: zodResolver(triageSchema),
    defaultValues: {
      transcript: "",
      source_language: "auto",
      target_language: "en",
      model_mode: "auto",
      age_months: 18,
      respiratory_rate_bpm: undefined,
    },
  });

  const formValues = watch();
  const errorMessage =
    localError ||
    triageStream.error ||
    getMutationError(audioMutation.error) ||
    getMutationError(videoMutation.error);

  const isRunning = triageStream.isStreaming;

  const onSubmit = handleSubmit(async (values) => {
    setLocalError(null);
    triageStream.reset();

    const request: TriageRequest = {
      transcript: values.transcript,
      source_language: values.source_language,
      target_language: values.target_language,
      model_mode: values.model_mode,
      patient: { age_months: values.age_months, sex: "unknown" },
      measurements: { respiratory_rate_bpm: values.respiratory_rate_bpm },
      context: { setting: "low_resource_clinic", frontend: "vercel_demo" },
    };
    setLastRequest(request);
    await triageStream.run(request);
  });

  function handleRefine(enrichedRequest: TriageRequest) {
    triageStream.run(enrichedRequest);
  }

  async function handleTranscribe() {
    if (!audioFile) {
      return;
    }

    setLocalError(null);

    try {
      const response = await audioMutation.mutateAsync({
        file: audioFile,
        sourceLanguage: formValues.source_language,
      });
      setValue("transcript", response.data.transcript, { shouldValidate: true });
    } catch (error) {
      setLocalError(getErrorMessage(error));
    }
  }

  async function handleAnalyzeVideo() {
    if (!videoFile) {
      return;
    }

    setLocalError(null);

    try {
      const response = await videoMutation.mutateAsync({
        file: videoFile,
        ageMonths: formValues.age_months,
      });

      if (typeof response.data.respiratory_rate_bpm === "number") {
        setValue("respiratory_rate_bpm", response.data.respiratory_rate_bpm, { shouldValidate: true });
      }
    } catch (error) {
      setLocalError(getErrorMessage(error));
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.94fr)_minmax(430px,1.06fr)]">
      <form className="grid gap-4" onSubmit={onSubmit}>
        <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-5 shadow-subtle">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-ink">Clinical intake</h2>
              <p className="text-sm leading-6 text-slate-600">
                Capture the case, choose the model route, and keep the final decision under human review.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {demoCases.map((demoCase) => (
                <Button
                  key={demoCase.label}
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setValue("source_language", demoCase.source_language, { shouldValidate: true });
                    setValue("target_language", "en", { shouldValidate: true });
                    setValue("model_mode", "auto", { shouldValidate: true });
                    setValue("age_months", 18, { shouldValidate: true });
                    setValue("respiratory_rate_bpm", demoCase.respiratory_rate_bpm, { shouldValidate: true });
                    setValue("transcript", demoCase.transcript, { shouldValidate: true });
                  }}
                >
                  {demoCase.label}
                </Button>
              ))}
            </div>
          </div>

          {errorMessage ? <Alert tone="error">{errorMessage}</Alert> : null}

          <ModeSelector
            health={health.data?.data}
            isCheckingHealth={health.isLoading}
            value={formValues.model_mode}
            register={register}
          />
          <LanguageSelector register={register} />

          <Field label="Child age" error={errors.age_months?.message}>
            <div className="grid grid-cols-[1fr_auto] items-center rounded-md border border-slate-300 bg-white focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100">
              <input
                className="min-h-10 min-w-0 rounded-md px-3 py-2 text-sm outline-none"
                type="number"
                min={0}
                max={216}
                {...register("age_months", { setValueAs: numberOrUndefined })}
              />
              <span className="px-3 text-sm text-slate-500">months</span>
            </div>
          </Field>

          <Field
            label="Transcript or symptom description"
            hint="The backend clinical tools and IMCI retrieval are disease-oriented, not limited to pneumonia."
            error={errors.transcript?.message}
          >
            <textarea
              className="min-h-40 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm leading-6 text-ink outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              {...register("transcript")}
            />
          </Field>

          <Field label="Respiratory rate" hint="Optional. Video analysis can fill this value." error={errors.respiratory_rate_bpm?.message}>
            <div className="grid grid-cols-[1fr_auto] items-center rounded-md border border-slate-300 bg-white focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100">
              <input
                className="min-h-10 min-w-0 rounded-md px-3 py-2 text-sm outline-none"
                type="number"
                min={0}
                max={120}
                placeholder="Optional"
                {...register("respiratory_rate_bpm", { setValueAs: numberOrUndefined })}
              />
              <span className="px-3 text-sm text-slate-500">bpm</span>
            </div>
          </Field>
        </section>

        <AudioUpload
          file={audioFile}
          isLoading={audioMutation.isPending}
          onFileChange={(file, error) => {
            setAudioFile(file);
            setLocalError(error ?? null);
          }}
          onTranscribe={handleTranscribe}
        />

        {audioMutation.data ? (
          <Alert tone="success">
            Audio transcribed. Detected language: {audioMutation.data.data.detected_language}. Duration:{" "}
            {audioMutation.data.data.duration_seconds.toFixed(1)}s.
          </Alert>
        ) : null}

        <VideoUpload
          file={videoFile}
          isLoading={videoMutation.isPending}
          onFileChange={(file, error) => {
            setVideoFile(file);
            setLocalError(error ?? null);
          }}
          onAnalyze={handleAnalyzeVideo}
        />

        {videoMutation.data ? (
          <Alert tone={videoMutation.data.data.respiratory_rate_bpm === null ? "warning" : "success"}>
            {videoMutation.data.data.respiratory_rate_bpm === null
              ? "Respiratory rate was uncertain. You can continue without video evidence."
              : `Respiratory rate estimated at ${videoMutation.data.data.respiratory_rate_bpm} bpm.`}
            {videoMutation.data.data.quality_flags.length > 0
              ? ` Quality flags: ${videoMutation.data.data.quality_flags.join(", ")}.`
              : null}
          </Alert>
        ) : null}

        <section className="flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2 text-sm leading-6 text-slate-600">
            <Badge tone="blue">Gemma 4 first</Badge>
            <Badge tone="teal">Offline capable</Badge>
            <span>Same workflow, selectable routing.</span>
          </div>
          <Button type="submit" variant="primary" disabled={isRunning}>
            {isRunning ? (
              <Spinner label="Running triage" />
            ) : (
              <>
                <PlayCircle className="h-4 w-4" aria-hidden="true" />
                Run triage
              </>
            )}
          </Button>
        </section>
      </form>

      <div className="grid content-start gap-4">
        <section className="rounded-md border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
            Demo guardrail
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Clinical decision support only. Final decisions remain with qualified medical staff.
          </p>
        </section>
        <section className="grid gap-3 rounded-md border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-ink">Demo proof</h2>
          <ol className="grid gap-2 text-sm leading-6 text-slate-600">
            <li className="flex items-start gap-2">
              <Badge tone="blue">Gemma 4</Badge>
              <span>Extracts multilingual clinical signals.</span>
            </li>
            <li className="flex items-start gap-2">
              <Badge tone="green">IMCI</Badge>
              <span>Grounds the recommendation with evidence.</span>
            </li>
            <li className="flex items-start gap-2">
              <Badge tone="teal">Offline</Badge>
              <span>Keeps the same workflow deployable in the field.</span>
            </li>
          </ol>
        </section>
        <TriageResult
          result={triageStream.result}
          meta={null}
          isLoading={isRunning}
          streamNodes={triageStream.nodes}
          lastRequest={lastRequest}
          onRefine={handleRefine}
        />
      </div>
    </div>
  );
}

function getMutationError(error: unknown) {
  return error ? getErrorMessage(error) : null;
}

function numberOrUndefined(value: unknown) {
  if (value === "" || value === null || typeof value === "undefined") {
    return undefined;
  }

  return Number(value);
}
