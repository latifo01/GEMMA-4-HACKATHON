import { useMutation } from "@tanstack/react-query";

import { transcribeAudio } from "../../services/api/audio";
import type { SourceLanguage } from "../../types/triage";

export function useAudioTranscription() {
  return useMutation({
    mutationFn: ({ file, sourceLanguage }: { file: File; sourceLanguage: SourceLanguage }) =>
      transcribeAudio(file, sourceLanguage),
  });
}
