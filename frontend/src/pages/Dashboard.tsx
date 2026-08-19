import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle, Cpu, HardDrive, MemoryStick, RefreshCw, Sparkles } from "lucide-react";
import { type ReactNode } from "react";
import { api } from "../lib/api";
import { useLiveEvents } from "../lib/useLiveEvents";
import { Button } from "../components/ui/Button";
import { Card, Stat } from "../components/ui/Card";
import { Badge } from "../components/ui/Feedback";
import { EventFeed } from "../components/EventFeed";

export function Dashboard() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });
  const status = useQuery({ queryKey: ["status"], queryFn: api.status, refetchInterval: 4000 });
  const digest = useQuery({ queryKey: ["digest"], queryFn: api.digest, staleTime: 120000 });
  const events = useLiveEvents();
  const s = status.data;

  return (
    <div className="stack">
      <div className="grid grid--stats">
        <Stat value={s?.cameras ?? "—"} label="Cameras" />
        <Stat value={s?.persons ?? "—"} label="Persons seen" />
        <Stat value={s?.events_24h ?? "—"} label="Events (24h)" />
        <Stat value={s?.behaviors_24h ?? "—"} label="Alerts (24h)" />
      </div>

      <Card title="System">
        <div className="grid grid--stats">
          <Meter icon={<HardDrive size={16} strokeWidth={1.5} />} label="VRAM free" value={s?.vram_free_mb != null ? `${(s.vram_free_mb / 1024).toFixed(1)} GB` : "n/a"} />
          <Meter icon={<Cpu size={16} strokeWidth={1.5} />} label="CPU" value={s?.cpu_percent != null ? `${s.cpu_percent.toFixed(0)}%` : "n/a"} />
          <Meter icon={<MemoryStick size={16} strokeWidth={1.5} />} label="RAM" value={s?.ram_percent != null ? `${s.ram_percent.toFixed(0)}%` : "n/a"} />
          <Meter icon={null} label="Uptime" value={s ? formatUptime(s.uptime_s) : "—"} />
        </div>
      </Card>

      <Card
        title="Daily digest"
        actions={
          <Button small variant="secondary" onClick={() => digest.refetch()} disabled={digest.isFetching}>
            <RefreshCw size={14} strokeWidth={1.5} /> Refresh
          </Button>
        }
      >
        <p style={{ margin: 0, lineHeight: 1.6 }}>{digest.data?.text ?? "Generating…"}</p>
        {digest.data && (
          <div style={{ marginTop: 8 }}>
            <Badge variant={digest.data.source === "llm" ? "live" : undefined}>
              <Sparkles size={12} strokeWidth={1.5} /> {digest.data.source === "llm" ? "AI-written" : "auto"} · {digest.data.events_24h} events
            </Badge>
          </div>
        )}
      </Card>

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

function Meter({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div>
      <div className="row muted" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {icon} {label}
      </div>
      <div style={{ fontFamily: "var(--font-heading)", fontSize: 24, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}

function formatUptime(seconds: number): string {
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
}
