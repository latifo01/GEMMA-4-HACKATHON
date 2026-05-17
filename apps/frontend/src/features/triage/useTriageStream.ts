import { flushSync } from "react-dom";
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

// Minimum time (ms) each node stays visually "running" before completing.
// Prevents steps from flickering past too fast to read.
const MIN_NODE_DISPLAY_MS = 400;

function initialNodes(): Record<StreamNode, NodeStatus> {
  return Object.fromEntries(ALL_NODES.map((n) => [n, "pending"])) as Record<StreamNode, NodeStatus>;
}

export function useTriageStream() {
  const [state, setState] = useState<StreamState>({
    nodes: initialNodes(),
    result: null,
    error: null,
    isStreaming: false,
  });

  // AbortController-based cancellation: each run() gets its own controller.
  // Aborting it cancels the fetch AND stops the event loop — no race condition.
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (request: TriageRequest) => {
    // Cancel any previous stream before starting a new one.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // flushSync: force React to commit the reset synchronously so the
    // loading UI appears immediately, before the first await below.
    flushSync(() => {
      setState({ nodes: initialNodes(), result: null, error: null, isStreaming: true });
    });

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
      flushSync(() => {
        setState((s) => ({ ...s, isStreaming: false, error: String(err) }));
      });
      return;
    }

    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => "Stream request failed");
      if (!controller.signal.aborted) {
        flushSync(() => {
          setState((s) => ({ ...s, isStreaming: false, error: text }));
        });
      }
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    // Track when each node started so we can enforce MIN_NODE_DISPLAY_MS.
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
            // flushSync: each node_started triggers an immediate visible render.
            flushSync(() => {
              setState((s) => ({ ...s, nodes: { ...s.nodes, [node]: "running" } }));
            });
          } else if (eventType === "node_completed") {
            const node = data.node as StreamNode;

            // If the node resolved faster than MIN_NODE_DISPLAY_MS, wait the
            // remainder so the "running" state is actually readable on screen.
            const elapsed = Date.now() - (nodeStartTimes[node] ?? 0);
            if (elapsed < MIN_NODE_DISPLAY_MS) {
              await new Promise<void>((resolve) =>
                setTimeout(resolve, MIN_NODE_DISPLAY_MS - elapsed)
              );
            }
            if (controller.signal.aborted) break;

            flushSync(() => {
              setState((s) => ({ ...s, nodes: { ...s.nodes, [node]: "completed" } }));
            });
          } else if (eventType === "result") {
            const result = data.data as TriageResultData;
            flushSync(() => {
              setState((s) => ({ ...s, isStreaming: false, result }));
            });
          } else if (eventType === "error") {
            const message = String((data as Record<string, unknown>).message ?? "Stream error");
            flushSync(() => {
              setState((s) => ({ ...s, isStreaming: false, error: message }));
            });
          }
        }
      }
    } finally {
      reader.releaseLock();
      // Guard: if the result event already set isStreaming=false, don't overwrite.
      setState((s) => (s.isStreaming ? { ...s, isStreaming: false } : s));
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    // No flushSync needed here: reset is called before run() in onSubmit,
    // and run() immediately does its own flushSync.
    setState({ nodes: initialNodes(), result: null, error: null, isStreaming: false });
  }, []);

  return { ...state, run, reset };
}
