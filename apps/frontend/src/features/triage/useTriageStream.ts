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
  const cancelRef = useRef(false);

  const run = useCallback(async (request: TriageRequest) => {
    cancelRef.current = false;
    setState({ nodes: initialNodes(), result: null, error: null, isStreaming: true });

    let response: Response;
    try {
      response = await fetch(`${env.apiBaseUrl}/triage/run/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "bypass-tunnel-reminder": "true",
        },
        body: JSON.stringify(request),
      });
    } catch (err) {
      setState((s) => ({ ...s, isStreaming: false, error: String(err) }));
      return;
    }

    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => "Stream request failed");
      setState((s) => ({ ...s, isStreaming: false, error: text }));
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done || cancelRef.current) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";

        for (const block of blocks) {
          const eventLine = block.split("\n").find((l) => l.startsWith("event: "));
          const dataLine = block.split("\n").find((l) => l.startsWith("data: "));
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
            setState((s) => ({ ...s, nodes: { ...s.nodes, [node]: "running" } }));
          } else if (eventType === "node_completed") {
            const node = data.node as StreamNode;
            setState((s) => ({ ...s, nodes: { ...s.nodes, [node]: "completed" } }));
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
    cancelRef.current = true;
    setState({ nodes: initialNodes(), result: null, error: null, isStreaming: false });
  }, []);

  return { ...state, run, reset };
}
