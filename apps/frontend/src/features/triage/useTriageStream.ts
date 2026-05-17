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

// Realistic per-node display durations (ms). The animation runs in parallel
// with the actual API request; Promise.all waits for whichever is slower.
const NODE_TIMINGS: Array<[StreamNode, number]> = [
  ["intake", 400],
  ["symptom_extraction", 2200],
  ["rag_retrieval", 1400],
  ["imci_reasoning", 1200],
  ["verification", 700],
  ["translation", 800],
];

function initialNodes(): Record<StreamNode, NodeStatus> {
  return Object.fromEntries(ALL_NODES.map((n) => [n, "pending"])) as Record<
    StreamNode,
    NodeStatus
  >;
}

export function useTriageStream() {
  const [state, setState] = useState<StreamState>({
    nodes: initialNodes(),
    result: null,
    error: null,
    isStreaming: false,
  });

  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (request: TriageRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ nodes: initialNodes(), result: null, error: null, isStreaming: true });

    // ── Real API call (non-streaming, proven stable) ─────────────────────────
    const fetchResult = async (): Promise<TriageResultData> => {
      const response = await fetch(`${env.apiBaseUrl}/triage/run`, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "bypass-tunnel-reminder": "true",
        },
        body: JSON.stringify(request),
      });
      if (!response.ok) {
        const text = await response.text().catch(() => "Request failed");
        throw new Error(text);
      }
      const json = (await response.json()) as { data: TriageResultData };
      return json.data;
    };

    // ── Visual progress animation (runs in parallel with the real call) ──────
    const animateNodes = async (): Promise<void> => {
      for (const [node, duration] of NODE_TIMINGS) {
        if (controller.signal.aborted) return;
        setState((s) => ({ ...s, nodes: { ...s.nodes, [node]: "running" } }));
        await new Promise<void>((resolve) => {
          const id = setTimeout(resolve, duration);
          controller.signal.addEventListener("abort", () => {
            clearTimeout(id);
            resolve();
          }, { once: true });
        });
        if (controller.signal.aborted) return;
        setState((s) => ({ ...s, nodes: { ...s.nodes, [node]: "completed" } }));
      }
    };

    // ── Race both; show result when both complete ────────────────────────────
    try {
      const [result] = await Promise.all([fetchResult(), animateNodes()]);
      if (controller.signal.aborted) return;
      setState((s) => ({ ...s, isStreaming: false, result }));
    } catch (err) {
      if (controller.signal.aborted) return;
      const message = err instanceof Error ? err.message : String(err);
      setState((s) => ({ ...s, isStreaming: false, error: message }));
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState({ nodes: initialNodes(), result: null, error: null, isStreaming: false });
  }, []);

  return { ...state, run, reset };
}
