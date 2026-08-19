import { useMutation, useQuery } from "@tanstack/react-query";
import { Bell, LogOut, Send } from "lucide-react";
import { useState } from "react";
import { api, SettingsSnapshot } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge, Spinner } from "../components/ui/Feedback";

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

      <NotificationsCard settings={s} />

      <Card title="Session">
        <p className="muted" style={{ marginTop: 0 }}>Forget the stored API key on this browser.</p>
        <Button variant="secondary" onClick={disconnect}>
          <LogOut size={16} strokeWidth={1.5} /> Disconnect
        </Button>
      </Card>
    </div>
  );
}

function NotificationsCard({ settings }: { settings: SettingsSnapshot }) {
  const n = settings.notifications;
  const [result, setResult] = useState<string | null>(null);
  const test = useMutation({
    mutationFn: api.notifyTest,
    onSuccess: () => setResult("sent"),
    onError: () => setResult("failed"),
  });

  return (
    <Card title="Notifications">
      <div className="between" style={{ padding: "8px 0", borderBottom: "1px solid var(--color-border)" }}>
        <span className="muted"><Bell size={15} strokeWidth={1.5} /> Webhook</span>
        {n.enabled ? <Badge variant="live">configured</Badge> : <Badge>not set</Badge>}
      </div>
      <Row label="Notify on" value={n.notify_on} />
      <Row label="Cooldown" value={`${n.cooldown_s}s`} />
      <div className="row" style={{ marginTop: 12 }}>
        <Button small onClick={() => test.mutate()} disabled={!n.enabled || test.isPending}>
          <Send size={14} strokeWidth={1.5} /> {test.isPending ? "Sending…" : "Send test"}
        </Button>
        {result && <span className="muted">{result === "sent" ? "✓ sent" : "✗ failed — check the URL"}</span>}
      </div>
      <p className="muted" style={{ fontSize: 13, marginBottom: 0, marginTop: 12 }}>
        Set <code>ARGOS_NOTIFY_WEBHOOK_URL</code> (ntfy / Home Assistant / Discord / Telegram) in{" "}
        <code>.env</code>, then restart.
      </p>
    </Card>
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
