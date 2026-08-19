import { AlertTriangle, MapPin, UserCheck, UserPlus } from "lucide-react";
import { ArgosEvent } from "../lib/api";
import { relativeTime } from "../lib/useLiveEvents";
import { EmptyState } from "./ui/Feedback";

const ICONS = { new_person: UserPlus, recognized: UserCheck, behavior: AlertTriangle, zone: MapPin };

export function EventFeed({ events }: { events: ArgosEvent[] }) {
  if (events.length === 0) return <EmptyState>No events yet — waiting for activity…</EmptyState>;
  return (
    <div className="feed">
      {events.map((e) => {
        const Icon = ICONS[e.kind as keyof typeof ICONS] ?? UserCheck;
        return (
          <div className="feed__item" key={e.id}>
            <Icon size={18} strokeWidth={1.5} color={iconColor(e.kind)} />
            <span>
              <strong>{label(e)}</strong>
              {e.camera ? <span className="muted"> · {e.camera}</span> : null}
            </span>
            <span className="feed__time">{relativeTime(e.ts)}</span>
          </div>
        );
      })}
    </div>
  );
}

function label(e: ArgosEvent): string {
  if (e.kind === "behavior") return `${e.label ?? "behaviour"} (${((e.score ?? 0) * 100).toFixed(0)}%)`;
  if (e.kind === "zone") return `Zone: ${e.label ?? "entry"}`;
  if (e.kind === "new_person") return "New person";
  if (e.kind === "recognized") return "Recognized person";
  return e.kind;
}

function iconColor(kind: string): string {
  if (kind === "behavior") return "var(--color-destructive)";
  if (kind === "zone") return "var(--color-warning)";
  return "var(--color-accent)";
}
