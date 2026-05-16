import { apiJson } from "./client";
import type { SessionData } from "../../types/sessions";

export function getSession(sessionId: string) {
  return apiJson<SessionData>(`/sessions/${encodeURIComponent(sessionId)}`);
}
