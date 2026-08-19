import { useQuery } from "@tanstack/react-query";
import { api, ArgosEvent } from "../lib/api";
import { EventFeed } from "../components/EventFeed";
import { Card } from "../components/ui/Card";
import { useLiveEvents } from "../lib/useLiveEvents";

export function Events() {
  const live = useLiveEvents(200);
  const history = useQuery({ queryKey: ["events"], queryFn: () => api.events(200) });

  // Merge live (SSE) with fetched history, de-duplicated by id, newest first.
  const merged = dedupe([...live, ...(history.data ?? [])]);

  return (
    <div className="grid" style={{ gridTemplateColumns: "1fr" }}>
      <Card title={`Events (${merged.length})`}>
        <EventFeed events={merged} />
      </Card>
    </div>
  );
}

function dedupe(events: ArgosEvent[]): ArgosEvent[] {
  const seen = new Set<string>();
  const out: ArgosEvent[] = [];
  for (const e of events.sort((a, b) => b.ts - a.ts)) {
    if (!seen.has(e.id)) {
      seen.add(e.id);
      out.push(e);
    }
  }
  return out;
}
