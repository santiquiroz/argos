import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle } from "lucide-react";
import { api } from "../lib/api";
import { useLiveEvents } from "../lib/useLiveEvents";
import { Card, Stat } from "../components/ui/Card";
import { EventFeed } from "../components/EventFeed";

export function Dashboard() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });
  const cameras = useQuery({ queryKey: ["cameras"], queryFn: api.cameras });
  const persons = useQuery({ queryKey: ["persons"], queryFn: api.persons, refetchInterval: 10000 });
  const events = useLiveEvents();

  const ready = health.data?.analyzers.filter((a) => a.available).length ?? 0;
  const total = health.data?.analyzers.length ?? 0;

  return (
    <div className="stack">
      <div className="grid grid--stats">
        <Stat value={cameras.data?.length ?? "—"} label="Cameras" />
        <Stat value={persons.data?.length ?? "—"} label="Persons seen" />
        <Stat value={`${ready}/${total}`} label="Analyzers ready" />
        <Stat value={health.data?.device ?? "—"} label="Inference device" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <Card title="Analyzers">
          <div className="stack" style={{ gap: 12 }}>
            {(health.data?.analyzers ?? []).map((a) => (
              <div className="row" key={a.name}>
                {a.available ? (
                  <CheckCircle2 size={18} strokeWidth={1.5} color="var(--color-live)" />
                ) : (
                  <Circle size={18} strokeWidth={1.5} color="var(--color-muted-foreground)" />
                )}
                <span style={{ textTransform: "capitalize" }}>{a.name}</span>
                <span className="muted" style={{ marginLeft: "auto", fontSize: 13 }}>
                  {a.available ? "ready" : "model not downloaded"}
                </span>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Live events">
          <EventFeed events={events.slice(0, 8)} />
        </Card>
      </div>
    </div>
  );
}
