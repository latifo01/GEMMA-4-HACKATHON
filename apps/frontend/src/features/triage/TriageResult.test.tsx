import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { TriageRequest, TriageResultData } from "../../types/triage";
import { TriageResult } from "./TriageResult";

const baseRequest: TriageRequest = {
  transcript: "The child has abdominal pain.",
  source_language: "en",
  target_language: "en",
  model_mode: "auto",
  patient: { age_months: 18, sex: "unknown" },
  measurements: {},
  context: { setting: "low_resource_clinic" },
};

const baseResult: TriageResultData = {
  session_id: "session-123",
  triage_color: "YELLOW",
  classification: "NEEDS_CLINICIAN_ASSESSMENT",
  human_review_required: true,
  extracted_symptoms: {},
  missing_information: [],
  tool_results: [],
  reasoning: "Classification needs clinician assessment.",
  recommendations: ["Treat according to local IMCI protocol."],
  translated_output: "",
  safety_flags: [],
  citations: [],
  model: { mode: "online", name: "models/gemma-4-26b-a4b-it" },
  errors: [],
};

describe("TriageResult", () => {
  it("offers refinement for vague complaints even without missing structured fields", () => {
    render(
      <TriageResult
        meta={null}
        result={{ ...baseResult, safety_flags: ["UNKNOWN_COMPLAINT"] }}
        isLoading={false}
        lastRequest={baseRequest}
        onRefine={vi.fn()}
      />,
    );

    expect(screen.getByText("Complaint unclear — add symptom details")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refine diagnosis" })).toBeDisabled();
  });
});
