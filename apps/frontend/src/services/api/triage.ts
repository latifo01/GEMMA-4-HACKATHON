import { apiJson } from "./client";
import type { TriageRequest, TriageResultData } from "../../types/triage";

export function runTriage(payload: TriageRequest) {
  return apiJson<TriageResultData>("/triage/run", payload);
}
