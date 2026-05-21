import { useState, useCallback, useRef } from "react";

export type AgentEvent =
  | { type: "plan"; content: string[] }
  | { type: "text"; content: string }
  | { type: "tool_calls"; content: { name: string; input: Record<string, unknown> }[] }
  | { type: "tool_results"; content: { id: string; output: string }[] }
  | { type: "done"; content: { session_id: string; iterations: number } }
  | { type: "error"; content: string };

interface UseAgentStreamReturn {
  events: AgentEvent[];
  running: boolean;
  run: (task: string, systemPrompt?: string) => void;
  clear: () => void;
}

export function useAgentStream(apiBase = ""): UseAgentStreamReturn {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(
    (task: string, systemPrompt = "") => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setEvents([]);
      setRunning(true);

      (async () => {
        try {
          const res = await fetch(`${apiBase}/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task, system_prompt: systemPrompt }),
            signal: ctrl.signal,
          });

          const reader = res.body!.getReader();
          const decoder = new TextDecoder();
          let buf = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buf += decoder.decode(value, { stream: true });
            const lines = buf.split("\n");
            buf = lines.pop() ?? "";

            for (const line of lines) {
              if (!line.startsWith("data: ")) continue;
              const raw = line.slice(6).trim();
              if (raw === "[DONE]") continue;
              try {
                const event = JSON.parse(raw) as AgentEvent;
                setEvents((prev) => [...prev, event]);
              } catch {
                // skip malformed
              }
            }
          }
        } catch (err: unknown) {
          if ((err as Error).name !== "AbortError") {
            setEvents((prev) => [...prev, { type: "error", content: String(err) }]);
          }
        } finally {
          setRunning(false);
        }
      })();
    },
    [apiBase]
  );

  const clear = useCallback(() => {
    abortRef.current?.abort();
    setEvents([]);
    setRunning(false);
  }, []);

  return { events, running, run, clear };
}
