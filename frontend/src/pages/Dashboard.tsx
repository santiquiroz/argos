import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, ArgosEvent } from "../lib/api";

// Minimal starter surface: health, analyzer availability, person count, and a live SSE event feed.
// A fuller UI (person profiles, behaviour timeline, enrollment, camera view) is on the roadmap.
export function Dashboard() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });
  const persons = useQuery({ queryKey: ["persons"], queryFn: api.persons, refetchInterval: 10000 });
  const live = useLiveEvents();

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 820, margin: "2rem auto", padding: "0 1rem" }}>
      <h1 style={{ letterSpacing: "-0.02em" }}>Argos</h1>
      <p style={{ color: "#666", marginTop: "-0.5rem" }}>
        Behavioural &amp; identity analytics — {health.data?.ingest ?? "…"} ingest on {health.data?.device ?? "…"}
      </p>

      <section style={card}>
        <h2 style={h2}>Analyzers</h2>
        <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
          {health.data?.analyzers.map((a) => (
            <li key={a.name}>
              {a.name} — {a.available ? "✅ ready" : "⚪ model not downloaded"}
            </li>
          )) ?? <li>loading…</li>}
        </ul>
      </section>

      <section style={card}>
        <h2 style={h2}>Persons ({persons.data?.length ?? 0})</h2>
        <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
          {persons.data?.slice(0, 10).map((p) => (
            <li key={p.id}>
              {p.name ?? <em>#{p.id.slice(0, 8)} (unenrolled)</em>}
            </li>
          )) ?? <li>loading…</li>}
        </ul>
      </section>

      <section style={card}>
        <h2 style={h2}>Live events</h2>
        {live.length === 0 ? (
          <p style={{ color: "#999" }}>Waiting for events…</p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {live.slice(0, 20).map((e) => (
              <li key={e.id}>
                <strong>{e.kind}</strong>
                {e.label ? ` · ${e.label} (${(e.score ?? 0).toFixed(2)})` : ""}
                {e.camera ? ` · ${e.camera}` : ""}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

function useLiveEvents(): ArgosEvent[] {
  const [events, setEvents] = useState<ArgosEvent[]>([]);
  useEffect(() => {
    const source = new EventSource("/api/events/stream");
    const onMessage = (e: MessageEvent) => setEvents((prev) => [JSON.parse(e.data), ...prev]);
    ["new_person", "recognized", "behavior"].forEach((kind) =>
      source.addEventListener(kind, onMessage as EventListener),
    );
    return () => source.close();
  }, []);
  return events;
}

const card: React.CSSProperties = {
  border: "1px solid #e5e5e5",
  borderRadius: 12,
  padding: "1rem 1.25rem",
  marginTop: "1rem",
};
const h2: React.CSSProperties = { fontSize: "1rem", margin: "0 0 0.5rem" };
