export type HealthData = {
  status: "ok";
  version: string;
  online_model_available: boolean;
  offline_model_available: boolean;
  selected_model_mode: "online" | "offline" | "unavailable";
  selected_model_name: string | null;
  rag_index_available: boolean;
  database_available: boolean;
};
