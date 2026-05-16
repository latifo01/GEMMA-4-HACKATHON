import { useQuery } from "@tanstack/react-query";

import { getHealth } from "../../services/api/health";

export function useBackendHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 30_000,
  });
}
