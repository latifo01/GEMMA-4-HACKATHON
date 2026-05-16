import { useMutation } from "@tanstack/react-query";

import { runTriage } from "../../services/api/triage";
import type { TriageRequest } from "../../types/triage";

export function useTriageRun() {
  return useMutation({
    mutationFn: (request: TriageRequest) => runTriage(request),
  });
}
