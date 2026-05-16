export type ApiMeta = {
  request_id?: string;
  model_mode?: "online" | "offline" | "unavailable" | string;
  duration_ms?: number;
};

export type ApiEnvelope<T> = {
  data: T;
  meta: ApiMeta;
};

export type ApiErrorEnvelope = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
  meta?: {
    request_id?: string;
  };
};
