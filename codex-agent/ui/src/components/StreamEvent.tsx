import React from "react";
import type { AgentEvent } from "../hooks/useAgentStream";

const styles: Record<string, React.CSSProperties> = {
  block: { padding: "10px 14px", borderRadius: 8, marginBottom: 8, fontSize: 14, lineHeight: 1.6 },
  plan: { background: "#1e3a5f", borderLeft: "3px solid #3b82f6" },
  text: { background: "#1a1a2e", borderLeft: "3px solid #a78bfa" },
  tool_calls: { background: "#1e2a1e", borderLeft: "3px solid #4ade80" },
  tool_results: { background: "#1e1e2e", borderLeft: "3px solid #f59e0b" },
  done: { background: "#1a2a1a", borderLeft: "3px solid #10b981", color: "#6ee7b7" },
  error: { background: "#2a1a1a", borderLeft: "3px solid #f87171", color: "#fca5a5" },
  label: { fontWeight: 600, textTransform: "uppercase", fontSize: 11, letterSpacing: 1, marginBottom: 4, opacity: 0.7 },
  code: { fontFamily: "monospace", whiteSpace: "pre-wrap", wordBreak: "break-all" },
};

export default function StreamEvent({ event }: { event: AgentEvent }) {
  const blockStyle = { ...styles.block, ...(styles[event.type] ?? {}) };

  return (
    <div style={blockStyle}>
      <div style={styles.label}>{event.type}</div>
      <EventBody event={event} />
    </div>
  );
}

function EventBody({ event }: { event: AgentEvent }) {
  if (event.type === "plan") {
    return (
      <ol style={{ paddingLeft: 18 }}>
        {event.content.map((step, i) => <li key={i}>{step}</li>)}
      </ol>
    );
  }
  if (event.type === "text") {
    return <p style={{ whiteSpace: "pre-wrap" }}>{event.content}</p>;
  }
  if (event.type === "tool_calls") {
    return (
      <>
        {event.content.map((tc, i) => (
          <div key={i} style={styles.code}>
            <strong>{tc.name}</strong>({JSON.stringify(tc.input, null, 2)})
          </div>
        ))}
      </>
    );
  }
  if (event.type === "tool_results") {
    return (
      <>
        {event.content.map((r, i) => (
          <div key={i} style={styles.code}>{r.output.slice(0, 500)}{r.output.length > 500 ? "…" : ""}</div>
        ))}
      </>
    );
  }
  if (event.type === "done") {
    return <span>Session {event.content.session_id} · {event.content.iterations} iteration(s)</span>;
  }
  if (event.type === "error") {
    return <span>{event.content}</span>;
  }
  return null;
}
