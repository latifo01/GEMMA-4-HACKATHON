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
  return Object.fromEntries(ALL_NODES.map((node) => [node, "pending"])) as Record<
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

    try {
      const response = await fetch(`${env.apiBaseUrl}/triage/run/stream`, {
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

      if (!response.body) {
        throw new Error("Streaming response body is unavailable.");
      }

      await readSseStream(response.body, controller.signal, (eventType, data) => {
        if (eventType === "node_started" && isStreamNode(data.node)) {
          const node = data.node;
          setState((current) => ({
            ...current,
            nodes: { ...current.nodes, [node]: "running" },
          }));
          return;
        }

        if (eventType === "node_completed" && isStreamNode(data.node)) {
          const node = data.node;
          setState((current) => ({
            ...current,
            nodes: { ...current.nodes, [node]: "completed" },
          }));
          return;
        }

        if (eventType === "result") {
          setState((current) => ({
            ...current,
            isStreaming: false,
            result: data.data as TriageResultData,
          }));
          return;
        }

        if (eventType === "error") {
          throw new Error(String(data.message ?? "Stream error"));
        }
      });

      if (controller.signal.aborted) return;
      setState((current) => ({ ...current, isStreaming: false }));
    } catch (err) {
      if (controller.signal.aborted) return;
      const message = err instanceof Error ? err.message : String(err);
      setState((current) => ({ ...current, isStreaming: false, error: message }));
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState({ nodes: initialNodes(), result: null, error: null, isStreaming: false });
  }, []);

  return { ...state, run, reset };
}

async function readSseStream(
  body: ReadableStream<Uint8Array>,
  signal: AbortSignal,
  onEvent: (eventType: string, data: Record<string, unknown>) => void,
) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (!signal.aborted) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        const parsed = parseSseBlock(block);
        if (parsed) {
          onEvent(parsed.eventType, parsed.data);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseSseBlock(block: string) {
  const eventLine = block.split("\n").find((line) => line.startsWith("event:"));
  const dataLine = block.split("\n").find((line) => line.startsWith("data:"));

  if (!eventLine || !dataLine) {
    return null;
  }

  return {
    eventType: eventLine.slice("event:".length).trim(),
    data: JSON.parse(dataLine.slice("data:".length).trim()) as Record<string, unknown>,
  };
}

function isStreamNode(value: unknown): value is StreamNode {
  return typeof value === "string" && ALL_NODES.includes(value as StreamNode);
}
