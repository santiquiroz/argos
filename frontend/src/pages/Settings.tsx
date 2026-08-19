import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, LogOut, Save, Send } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { api, SettingsSnapshot, SettingsUpdate } from "../lib/api";
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
        <p className="muted" style={{ fontSize: 13, marginBottom: 0 }}>Device/ingest change in <code>.env</code> + restart.</p>
      </Card>

      <Card title="Analyzers">
        {Object.entries(s.analyzers).map(([name, on]) => (
          <Row key={name} label={name} value={on ? "enabled" : "disabled"} />
        ))}
      </Card>

      <NotificationsCard snapshot={s} />
      <RetentionCard snapshot={s} />

      <Card title="Session">
        <p className="muted" style={{ marginTop: 0 }}>Forget the stored API key on this browser.</p>
        <Button variant="secondary" onClick={disconnect}>
          <LogOut size={16} strokeWidth={1.5} /> Disconnect
        </Button>
      </Card>
    </div>
  );
}

function useSettingsSave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SettingsUpdate) => api.updateSettings(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });
}

function NotificationsCard({ snapshot }: { snapshot: SettingsSnapshot }) {
  const n = snapshot.notifications;
  const save = useSettingsSave();
  const test = useMutation({ mutationFn: api.notifyTest });
  const [url, setUrl] = useState(n.webhook_url);
  const [on, setOn] = useState(n.notify_on);
  const [cooldown, setCooldown] = useState(n.cooldown_s);
  useEffect(() => { setUrl(n.webhook_url); setOn(n.notify_on); setCooldown(n.cooldown_s); }, [n.webhook_url, n.notify_on, n.cooldown_s]);

  return (
    <Card title="Notifications">
      <div className="between" style={{ paddingBottom: 8 }}>
        <span className="muted"><Bell size={15} strokeWidth={1.5} /> Webhook</span>
        {n.enabled ? <Badge variant="live">configured</Badge> : <Badge>not set</Badge>}
      </div>
      <div className="stack" style={{ gap: 10 }}>
        <Field label="Webhook URL (ntfy / Home Assistant / Discord / Telegram)">
          <input className="input" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://ntfy.sh/your-topic" />
        </Field>
        <div className="row" style={{ gap: 10 }}>
          <Field label="Notify on"><input className="input" value={on} onChange={(e) => setOn(e.target.value)} placeholder="behavior,new_person,zone" /></Field>
          <Field label="Cooldown (s)"><input className="input" type="number" value={cooldown} onChange={(e) => setCooldown(Number(e.target.value))} /></Field>
        </div>
        <div className="row">
          <Button small onClick={() => save.mutate({ notify_webhook_url: url, notify_on: on, notify_cooldown_s: cooldown })} disabled={save.isPending}>
            <Save size={14} strokeWidth={1.5} /> {save.isPending ? "Saving…" : "Save"}
          </Button>
          <Button small variant="secondary" onClick={() => test.mutate()} disabled={!n.enabled || test.isPending}>
            <Send size={14} strokeWidth={1.5} /> Test
          </Button>
          {test.isSuccess && <span className="muted">✓ sent</span>}
          {test.isError && <span className="muted">✗ failed</span>}
        </div>
      </div>
    </Card>
  );
}

function RetentionCard({ snapshot }: { snapshot: SettingsSnapshot }) {
  const save = useSettingsSave();
  const [crops, setCrops] = useState(snapshot.retention_days.crops);
  const [emb, setEmb] = useState(snapshot.retention_days.embeddings);
  const [evt, setEvt] = useState(snapshot.retention_days.events);
  useEffect(() => {
    setCrops(snapshot.retention_days.crops);
    setEmb(snapshot.retention_days.embeddings);
    setEvt(snapshot.retention_days.events);
  }, [snapshot.retention_days.crops, snapshot.retention_days.embeddings, snapshot.retention_days.events]);

  return (
    <Card title="Retention (days)">
      <div className="row" style={{ gap: 10 }}>
        <Field label="Crops"><input className="input" type="number" value={crops} onChange={(e) => setCrops(Number(e.target.value))} /></Field>
        <Field label="Embeddings"><input className="input" type="number" value={emb} onChange={(e) => setEmb(Number(e.target.value))} /></Field>
        <Field label="Events"><input className="input" type="number" value={evt} onChange={(e) => setEvt(Number(e.target.value))} /></Field>
      </div>
      <Button small style={{ marginTop: 12 }} onClick={() => save.mutate({ retain_crops_days: crops, retain_embeddings_days: emb, retain_events_days: evt })} disabled={save.isPending}>
        <Save size={14} strokeWidth={1.5} /> Save
      </Button>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="field" style={{ flex: 1 }}>
      <label className="field__label">{label}</label>
      {children}
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
