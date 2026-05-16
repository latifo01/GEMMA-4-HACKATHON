import { describe, expect, it, vi } from "vitest";

import { ApiError, apiJson } from "./client";

describe("apiJson", () => {
  it("returns the shared backend envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: { status: "ok" }, meta: { request_id: "req" } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(apiJson<{ status: string }>("/health")).resolves.toMatchObject({
      data: { status: "ok" },
      meta: { request_id: "req" },
    });
  });

  it("throws normalized backend errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "MODEL_UNAVAILABLE", message: "No model is available." },
            meta: { request_id: "req" },
          }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(apiJson("/triage/run")).rejects.toThrow(ApiError);
  });
});
