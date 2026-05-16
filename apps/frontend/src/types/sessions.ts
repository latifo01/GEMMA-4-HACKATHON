export type SessionData = {
  session_id: string;
  status: "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  model_mode: string | null;
  request: Record<string, unknown>;
  result: Record<string, unknown> | null;
  errors: Array<Record<string, unknown>>;
};
