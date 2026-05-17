import { useCallback, useRef, useState } from "react";

import { env } from "../../app/env";
import type { TriageRequest, TriageResultData } from "../../types/triage";

export type StreamNode =
  | "intake"
  | "symptom_extraction"
  | "rag_retrieval"
  | "imci_reasoning"
  | "verification"
  | "translation";

export type NodeStatus = "pending" | "running" | "completed";

export type StreamState = {
  nodes: Record<StreamNode, NodeStatus>;
  result: TriageResultData | null;
  error: string | null;
  isStreaming: boolean;
};

const ALL_NODES: StreamNode[] = [
  "intake",
  "symptom_extraction",
  "rag_retrieval",
  "imci_reasoning",
  "verification",
  "translation",
];

// Minimum time each node stays visually "running" before completing.
const MIN_NODE_DISPLAY_MS = 500;

function initialNodes(): Record<StreamNode, NodeStatus> {
  return Object.fromEntries(ALL_NODES.map((n) => [n, "pending"])) as Record<StreamNode, NodeStatus>;
}

// Yield to the browser event loop, letting React commit pending state updates
// before continuing. Safer than flushSync for React 19 concurrent mode.
function tick(ms = 0): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function useTriageStream() {
  const [state, setState] = useState<StreamState>({
    nodes: initialNodes(),
    result: null,
    error: null,
    isStreaming: false,
  });

  // Each run() gets its own AbortController.
  // Aborting cancels the fetch AND breaks the reader loop — no race condition.
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (request: TriageRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ nodes: initialNodes(), result: null, error: null, isStreaming: true });
    // Yield once so the loading UI renders before the fetch starts.
    await tick();

    let response: Response;
    try {
      response = await fetch(`${env.apiBaseUrl}/triage/run/stream`, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "bypass-tunnel-reminder": "true",
        },
        body: JSON.stringify(request),
      });
    } catch (err) {
      if (controller.signal.aborted) return;
      setState((s) => ({ ...s, isStreaming: false, error: String(err) }));
      return;
    }

    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => "Stream request failed");
      if (!controller.signal.aborted) {
        setState((s) => ({ ...s, isStreaming: false, error: text }));
      }
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    const nodeStartTimes: Partial<Record<StreamNode, number>> = {};

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done || controller.signal.aborted) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";

        for (const block of blocks) {
          if (controller.signal.aborted) break;

          const lines = block.split("\n");
          const eventLine = lines.find((l) => l.startsWith("event: "));
          const dataLine = lines.find((l) => l.startsWith("data: "));
          if (!eventLine || !dataLine) continue;

          const eventType = eventLine.slice(7).trim();
          let data: Record<string, unknown>;
          try {
            data = JSON.parse(dataLine.slice(6)) as Record<string, unknown>;
          } catch {
            continue;
          }

          if (eventType === "node_started") {
            const node = data.node as StreamNode;
            nodeStartTimes[node] = Date.now();
            setState((s) => ({ ...s, nodes: { ...s.nodes, [node]: "running" } }));
            // Yield so React renders "running" before the next event is processed.
            await tick();

          } else if (eventType === "node_completed") {
            const node = data.node as StreamNode;
            // Enforce minimum display time so fast nodes are readable on screen.
            const elapsed = Date.now() - (nodeStartTimes[node] ?? 0);
            const remaining = MIN_NODE_DISPLAY_MS - elapsed;
            if (remaining > 0) {
              await tick(remaining);
            }
            if (controller.signal.aborted) break;
            setState((s) => ({ ...s, nodes: { ...s.nodes, [node]: "completed" } }));
            await tick();

          } else if (eventType === "result") {
            const result = data.data as TriageResultData;
            setState((s) => ({ ...s, isStreaming: false, result }));

          } else if (eventType === "error") {
            const message = String((data as Record<string, unknown>).message ?? "Stream error");
            setState((s) => ({ ...s, isStreaming: false, error: message }));
          }
        }
      }
    } finally {
      reader.releaseLock();
      setState((s) => (s.isStreaming ? { ...s, isStreaming: false } : s));
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState({ nodes: initialNodes(), result: null, error: null, isStreaming: false });
  }, []);

  return { ...state, run, reset };
}
