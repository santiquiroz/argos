import { useEffect, useState } from "react";
import { ArgosEvent, eventStreamUrl } from "./api";

// Subscribe to the server-sent event stream of live detections/alerts.
export function useLiveEvents(max = 100): ArgosEvent[] {
  const [events, setEvents] = useState<ArgosEvent[]>([]);
  useEffect(() => {
    const source = new EventSource(eventStreamUrl());
    const onMessage = (e: MessageEvent) =>
      setEvents((prev) => [JSON.parse(e.data), ...prev].slice(0, max));
    ["new_person", "recognized", "behavior"].forEach((kind) =>
      source.addEventListener(kind, onMessage as EventListener),
    );
    return () => source.close();
  }, [max]);
  return events;
}

export function relativeTime(ts: number): string {
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
