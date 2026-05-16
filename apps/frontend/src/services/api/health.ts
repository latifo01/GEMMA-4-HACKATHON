import { apiJson } from "./client";
import type { HealthData } from "../../types/health";

export function getHealth() {
  return apiJson<HealthData>("/health");
}
