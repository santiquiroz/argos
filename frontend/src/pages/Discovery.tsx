import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Plus, Radar, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { api, DiscoveredCamera } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge, EmptyState, Spinner } from "../components/ui/Feedback";

export function Discovery() {
  const qc = useQueryClient();
  const [subnet, setSubnet] = useState("");
  const [audit, setAudit] = useState(true);

  const scan = useMutation({
    mutationFn: () => api.scan({ subnet: subnet || null, sweep: true, audit_credentials: audit }),
  });
  const addCam = useMutation({
    mutationFn: ({ name, url }: { name: string; url: string }) => api.addCamera(name, url),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cameras"] }),
  });

  const results = scan.data ?? [];

  return (
    <div className="stack">
      <Card title="Scan your network">
        <p className="muted" style={{ marginTop: 0 }}>
          Finds cameras/DVRs on your LAN and checks whether any still use a default password. Audits
          devices you own only.
        </p>
        <div className="row" style={{ alignItems: "flex-end", gap: 12, flexWrap: "wrap" }}>
          <div className="field" style={{ flex: "0 0 220px" }}>
            <label className="field__label">Subnet (optional)</label>
            <input className="input" value={subnet} onChange={(e) => setSubnet(e.target.value)} placeholder="auto (192.168.1.0/24)" />
          </div>
          <label className="row" style={{ height: 44, gap: 8 }}>
            <input type="checkbox" checked={audit} onChange={(e) => setAudit(e.target.checked)} />
            Audit default credentials
          </label>
          <Button onClick={() => scan.mutate()} disabled={scan.isPending}>
            {scan.isPending ? "Scanning…" : (<><Radar size={16} strokeWidth={1.5} /> Scan</>)}
          </Button>
        </div>
      </Card>

      {scan.isPending && <Card><div className="row"><Spinner /> Scanning the network…</div></Card>}

      {scan.isSuccess && (
        <Card title={`Results (${results.length})`}>
          {results.length === 0 ? (
            <EmptyState>No devices found. Try a specific --subnet, or check cameras are powered and ONVIF/RTSP is on.</EmptyState>
          ) : (
            <div className="stack" style={{ gap: 16 }}>
              {results.map((cam) => (
                <DeviceRow key={cam.ip} cam={cam} onAdd={(name, url) => addCam.mutate({ name, url })} />
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function DeviceRow({ cam, onAdd }: { cam: DiscoveredCamera; onAdd: (name: string, url: string) => void }) {
  return (
    <div style={{ border: "1px solid var(--color-border)", borderRadius: 8, padding: 16 }}>
      <div className="between">
        <div className="row">
          <strong style={{ fontFamily: "var(--font-heading)" }}>{cam.ip}</strong>
          <span className="muted">{cam.model ?? cam.vendor}</span>
          <span className="muted">· {cam.channels} ch</span>
        </div>
        {cam.insecure ? (
          <Badge variant="danger"><AlertTriangle size={13} strokeWidth={1.5} /> default password</Badge>
        ) : (
          <Badge variant="live"><ShieldCheck size={13} strokeWidth={1.5} /> secure</Badge>
        )}
      </div>
      {cam.insecure && (
        <p className="muted" style={{ fontSize: 13, margin: "8px 0 0" }}>
          Accepts <code>{cam.insecure_default_credential}</code> — change it in the device web UI.
        </p>
      )}
      <div className="stack" style={{ gap: 6, marginTop: 12 }}>
        {cam.rtsp_urls.map((url, i) => (
          <div className="between" key={url}>
            <code style={{ fontSize: 12, color: "var(--color-muted-foreground)", overflow: "hidden", textOverflow: "ellipsis" }}>
              {url}
            </code>
            <Button small variant="secondary" onClick={() => onAdd(`cam${cam.ip.split(".").pop()}_${i + 1}`, url)}>
              <Plus size={14} strokeWidth={1.5} /> Add
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
