import { Activity, Cloud, Database, Laptop, Server } from "lucide-react";

import { Badge } from "../ui/Badge";
import { Spinner } from "../ui/Spinner";
import { useBackendHealth } from "../../features/health/useBackendHealth";

export function BackendStatus() {
  const health = useBackendHealth();

  if (health.isLoading) {
    return (
      <Badge tone="neutral">
        <Spinner label="Checking backend" />
      </Badge>
    );
  }

  if (health.isError || !health.data) {
    return (
      <Badge tone="red">
        <Server className="h-3.5 w-3.5" aria-hidden="true" />
        Backend offline
      </Badge>
    );
  }

  const data = health.data.data;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge tone="green">
        <Activity className="h-3.5 w-3.5" aria-hidden="true" />
        API {data.version}
      </Badge>
      <Badge tone={data.online_model_available ? "blue" : "amber"}>
        <Cloud className="h-3.5 w-3.5" aria-hidden="true" />
        Gemma 4
      </Badge>
      <Badge tone={data.offline_model_available ? "teal" : "amber"}>
        <Laptop className="h-3.5 w-3.5" aria-hidden="true" />
        Offline
      </Badge>
      <Badge tone={data.rag_index_available ? "green" : "amber"}>
        <Database className="h-3.5 w-3.5" aria-hidden="true" />
        RAG
      </Badge>
    </div>
  );
}
