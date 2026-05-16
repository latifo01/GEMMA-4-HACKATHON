import { apiForm } from "./client";
import type { VideoAnalysisData } from "../../types/media";

export function analyzeVideo(file: File, ageMonths?: number | null) {
  const body = new FormData();
  body.append("file", file);

  if (typeof ageMonths === "number") {
    body.append("age_months", String(ageMonths));
  }

  return apiForm<VideoAnalysisData>("/video/analyze", body);
}
