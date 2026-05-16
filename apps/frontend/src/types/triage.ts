export type ModelMode = "auto" | "online" | "offline";
export type SourceLanguage = "auto" | "en" | "fr" | "ar-SD";
export type TargetLanguage = "en" | "fr" | "ar-SD";

export type TriageRequest = {
  session_id?: string | null;
  transcript: string;
  source_language: SourceLanguage;
  target_language: TargetLanguage;
  model_mode: ModelMode;
  patient: Record<string, unknown>;
  measurements: Record<string, unknown>;
  context: Record<string, unknown>;
};

export type TriageResultData = {
  session_id: string;
  triage_color: string;
  classification: string;
  human_review_required: boolean;
  extracted_symptoms: Record<string, unknown>;
  missing_information: string[];
  tool_results: Array<Record<string, unknown>>;
  reasoning: string;
  recommendations: string[];
  translated_output: string;
  safety_flags: string[];
  citations: Array<Record<string, unknown>>;
  model: {
    mode?: string;
    name?: string;
    provider?: string;
    [key: string]: unknown;
  };
  errors: Array<Record<string, unknown>>;
};
