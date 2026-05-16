import { apiForm } from "./client";
import type { AudioTranscriptionData } from "../../types/media";
import type { SourceLanguage } from "../../types/triage";

export function transcribeAudio(file: File, sourceLanguage: SourceLanguage) {
  const body = new FormData();
  body.append("file", file);
  body.append("source_language", sourceLanguage);

  return apiForm<AudioTranscriptionData>("/audio/transcribe", body);
}
