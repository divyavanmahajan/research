import React, { useRef, useEffect, useState } from "react";
import { useAgentStream } from "../hooks/useAgentStream";
import StreamEvent from "./StreamEvent";

const s: Record<string, React.CSSProperties> = {
  panel: { display: "flex", flexDirection: "column", height: "100vh", maxWidth: 860, margin: "0 auto" },
  header: { padding: "16px 20px", borderBottom: "1px solid #2d2d3d", display: "flex", alignItems: "center", gap: 12 },
  title: { fontSize: 18, fontWeight: 700, color: "#a78bfa" },
  badge: { fontSize: 11, padding: "2px 8px", borderRadius: 12, background: "#2d2d3d", color: "#94a3b8" },
  feed: { flex: 1, overflowY: "auto", padding: "16px 20px" },
  empty: { color: "#475569", textAlign: "center", marginTop: 80, fontSize: 15 },
  form: { display: "flex", gap: 10, padding: "14px 20px", borderTop: "1px solid #2d2d3d" },
  input: {
    flex: 1, background: "#1e1e2e", border: "1px solid #3d3d5c", borderRadius: 8,
    color: "#e2e8f0", padding: "10px 14px", fontSize: 14, outline: "none",
  },
  btn: {
    padding: "10px 20px", borderRadius: 8, border: "none", cursor: "pointer",
    fontWeight: 600, fontSize: 14,
  },
  runBtn: { background: "#7c3aed", color: "#fff" },
  stopBtn: { background: "#991b1b", color: "#fff" },
  clearBtn: { background: "#1e293b", color: "#94a3b8", border: "1px solid #2d2d3d" },
};

export default function ChatPanel() {
  const { events, running, run, clear } = useAgentStream();
  const [task, setTask] = useState("");
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [events]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = task.trim();
    if (!trimmed || running) return;
    run(trimmed);
    setTask("");
  }

  return (
    <div style={s.panel}>
      <div style={s.header}>
        <span style={s.title}>Codex Agent</span>
        {running && <span style={{ ...s.badge, background: "#1e3a5f", color: "#60a5fa" }}>● running</span>}
      </div>

      <div ref={feedRef} style={s.feed}>
        {events.length === 0 ? (
          <p style={s.empty}>Enter a task below to start the agent.</p>
        ) : (
          events.map((ev, i) => <StreamEvent key={i} event={ev} />)
        )}
      </div>

      <form onSubmit={handleSubmit} style={s.form}>
        <input
          style={s.input}
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="Describe a task for the agent…"
          disabled={running}
        />
        {running ? (
          <button type="button" style={{ ...s.btn, ...s.stopBtn }} onClick={clear}>Stop</button>
        ) : (
          <button type="submit" style={{ ...s.btn, ...s.runBtn }} disabled={!task.trim()}>Run</button>
        )}
        <button type="button" style={{ ...s.btn, ...s.clearBtn }} onClick={clear}>Clear</button>
      </form>
    </div>
  );
}
