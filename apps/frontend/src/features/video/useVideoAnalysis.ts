import { useMutation } from "@tanstack/react-query";

import { analyzeVideo } from "../../services/api/video";

export function useVideoAnalysis() {
  return useMutation({
    mutationFn: ({ file, ageMonths }: { file: File; ageMonths?: number | null }) =>
      analyzeVideo(file, ageMonths),
  });
}
