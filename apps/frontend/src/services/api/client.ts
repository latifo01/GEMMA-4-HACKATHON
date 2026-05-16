import { env } from "../../app/env";
import { normalizeApiError, type AppError } from "../../lib/errors";
import type { ApiEnvelope } from "../../types/api";

export class ApiError extends Error {
  readonly code: string;
  readonly status?: number;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(error: AppError) {
    super(error.message);
    this.name = "ApiError";
    this.code = error.code;
    this.status = error.status;
    this.requestId = error.requestId;
    this.details = error.details;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<ApiEnvelope<T>> {
  let response: Response;

  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      ...options,
      headers: withTunnelBypass(options.headers),
    });
  } catch {
    throw new ApiError(normalizeApiError(null));
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(normalizeApiError(payload, response.status));
  }

  return payload as ApiEnvelope<T>;
}

export function apiJson<T>(path: string, payload?: unknown): Promise<ApiEnvelope<T>> {
  return apiFetch<T>(path, {
    method: payload ? "POST" : "GET",
    headers: {
      "Content-Type": "application/json",
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

export function apiForm<T>(path: string, body: FormData): Promise<ApiEnvelope<T>> {
  return apiFetch<T>(path, {
    method: "POST",
    body,
  });
}

function withTunnelBypass(headersInit?: HeadersInit) {
  const headers = new Headers(headersInit);

  if (env.apiBaseUrl.includes(".loca.lt")) {
    headers.set("bypass-tunnel-reminder", "true");
  }

  return headers;
}
