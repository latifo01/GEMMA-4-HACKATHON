export type AppError = {
  code: string;
  message: string;
  status?: number;
  requestId?: string;
  details?: unknown;
};

export function normalizeApiError(payload: unknown, status?: number): AppError {
  if (isBackendError(payload)) {
    const requestId = payload.meta?.request_id;

    return {
      code: payload.error.code,
      message: mapBackendMessage(payload.error.code, payload.error.message),
      status,
      requestId,
      details: payload.error.details,
    };
  }

  return {
    code: "NETWORK_ERROR",
    message: "Backend is unreachable. Check the API URL or backend deployment.",
    status,
  };
}

export function getErrorMessage(error: unknown): string {
  if (isAppApiError(error)) {
    return error.requestId ? `${error.message} Request id: ${error.requestId}` : error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected error. Please retry.";
}

function isAppApiError(error: unknown): error is Error & { requestId?: string } {
  return error instanceof Error && error.name === "ApiError";
}

function mapBackendMessage(code: string, fallback: string) {
  const messages: Record<string, string> = {
    MODEL_UNAVAILABLE: "The selected model mode is not available. Try Auto or another mode.",
    VALIDATION_ERROR: "Some input is invalid. Please review the form.",
    TRANSCRIPTION_FAILED: "Audio transcription failed. You can type the transcript manually.",
    VIDEO_ANALYSIS_FAILED: "Video analysis failed. You can continue without video.",
    TRIAGE_VERIFICATION_FAILED: "The triage workflow failed a safety check. Please retry.",
  };

  return messages[code] ?? fallback;
}

function isBackendError(value: unknown): value is {
  error: { code: string; message: string; details?: unknown };
  meta?: { request_id?: string };
} {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as { error?: unknown }).error === "object"
  );
}
