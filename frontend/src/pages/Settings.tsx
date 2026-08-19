import { useQuery } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Spinner } from "../components/ui/Feedback";

export function Settings() {
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  if (settings.isLoading || !settings.data) return <Spinner />;
  const s = settings.data;

  const disconnect = () => {
    localStorage.removeItem("argos_api_key");
    location.reload();
  };

  return (
    <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
      <Card title="Inference">
        <Row label="Device" value={s.device} />
        <Row label="Ingest" value={s.ingest} />
        <Row label="Prefer fp16" value={s.prefer_fp16 ? "yes" : "no"} />
        {s.ingest === "frigate" && <Row label="Frigate URL" value={s.frigate_url} />}
      </Card>

      <Card title="Analyzers">
        {Object.entries(s.analyzers).map(([name, on]) => (
          <Row key={name} label={name} value={on ? "enabled" : "disabled"} />
        ))}
      </Card>

      <Card title="Retention (days)">
        {Object.entries(s.retention_days).map(([name, days]) => (
          <Row key={name} label={name} value={String(days)} />
        ))}
        <p className="muted" style={{ fontSize: 13, marginBottom: 0 }}>
          Configure these and analyzer toggles in <code>.env</code>, then restart. (Editing from the
          UI is on the roadmap.)
        </p>
      </Card>

      <Card title="Session">
        <p className="muted" style={{ marginTop: 0 }}>Forget the stored API key on this browser.</p>
        <Button variant="secondary" onClick={disconnect}>
          <LogOut size={16} strokeWidth={1.5} /> Disconnect
        </Button>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="between" style={{ padding: "8px 0", borderBottom: "1px solid var(--color-border)" }}>
      <span className="muted" style={{ textTransform: "capitalize" }}>{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  );
}
