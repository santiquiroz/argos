import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MousePointerClick, Trash2 } from "lucide-react";
import { type MouseEvent as ReactMouseEvent, useState } from "react";
import { api, mjpegUrl, Zone } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge, EmptyState } from "../components/ui/Feedback";

type Draft = { name: string; kind: "alert" | "ignore"; points: [number, number][] };
const EMPTY: Draft = { name: "", kind: "alert", points: [] };

export function Zones() {
  const qc = useQueryClient();
  const cameras = useQuery({ queryKey: ["cameras"], queryFn: api.cameras });
  const [camera, setCamera] = useState<string>("");
  const active = camera || cameras.data?.[0]?.name || "";
  const zones = useQuery({ queryKey: ["zones", active], queryFn: () => api.zones(active), enabled: !!active });
  const [draft, setDraft] = useState<Draft>(EMPTY);

  const save = useMutation({
    mutationFn: () => api.addZone({ camera: active, name: draft.name, kind: draft.kind, points: draft.points }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["zones", active] });
      setDraft(EMPTY);
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.removeZone(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zones", active] }),
  });

  if ((cameras.data ?? []).length === 0) {
    return <Card><EmptyState>Add a camera first, then draw zones on its view.</EmptyState></Card>;
  }

  const addPoint = (e: ReactMouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setDraft((d) => ({ ...d, points: [...d.points, [round(x), round(y)]] }));
  };

  return (
    <div className="stack">
      <div className="between">
        <div className="field" style={{ flex: "0 0 220px" }}>
          <label className="field__label">Camera</label>
          <select className="input" value={active} onChange={(e) => setCamera(e.target.value)}>
            {(cameras.data ?? []).map((c) => (
              <option key={c.name} value={c.name}>{c.name}</option>
            ))}
          </select>
        </div>
        <p className="muted" style={{ fontSize: 13, maxWidth: 360 }}>
          <MousePointerClick size={14} strokeWidth={1.5} /> Click the view to add polygon points.
          <b> Alert</b> zones fire on entry; <b>ignore</b> zones mask out noise (a tree, the street).
        </p>
      </div>

      <div style={{ position: "relative", aspectRatio: "16/9", borderRadius: 12, overflow: "hidden", border: "1px solid var(--color-border)", background: "#0b1220" }}>
        <img src={mjpegUrl(active)} alt="" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
        <svg
          viewBox="0 0 1 1"
          preserveAspectRatio="none"
          onClick={addPoint}
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", cursor: "crosshair" }}
        >
          {(zones.data ?? []).map((z) => (
            <ZonePolygon key={z.id} zone={z} />
          ))}
          {draft.points.length > 0 && (
            <>
              <polyline
                points={draft.points.map((p) => `${p[0]},${p[1]}`).join(" ")}
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth={2}
                vectorEffect="non-scaling-stroke"
                strokeDasharray="4 3"
              />
              {draft.points.map((p, i) => (
                <circle key={i} cx={p[0]} cy={p[1]} r={5} fill="var(--color-accent)" vectorEffect="non-scaling-stroke" />
              ))}
            </>
          )}
        </svg>
      </div>

      <Card title="New zone">
        <div className="row" style={{ alignItems: "flex-end", gap: 12, flexWrap: "wrap" }}>
          <div className="field" style={{ flex: "0 0 180px" }}>
            <label className="field__label">Name</label>
            <input className="input" value={draft.name} onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))} placeholder="driveway" />
          </div>
          <div className="field" style={{ flex: "0 0 140px" }}>
            <label className="field__label">Kind</label>
            <select className="input" value={draft.kind} onChange={(e) => setDraft((d) => ({ ...d, kind: e.target.value as Draft["kind"] }))}>
              <option value="alert">alert (tripwire)</option>
              <option value="ignore">ignore (mask)</option>
            </select>
          </div>
          <span className="muted">{draft.points.length} point(s)</span>
          <Button onClick={() => save.mutate()} disabled={!draft.name || draft.points.length < 3 || save.isPending}>
            {save.isPending ? "Saving…" : "Save zone"}
          </Button>
          <Button variant="secondary" onClick={() => setDraft(EMPTY)} disabled={draft.points.length === 0}>Clear</Button>
        </div>
      </Card>

      <Card title={`Zones on ${active} (${zones.data?.length ?? 0})`}>
        {(zones.data ?? []).length === 0 ? (
          <EmptyState>No zones yet. Click the view above to draw one.</EmptyState>
        ) : (
          <div className="stack" style={{ gap: 8 }}>
            {(zones.data ?? []).map((z) => (
              <div className="between" key={z.id} style={{ padding: "8px 0", borderBottom: "1px solid var(--color-border)" }}>
                <div className="row">
                  <Badge variant={z.kind === "alert" ? "warning" : undefined}>{z.kind}</Badge>
                  <strong style={{ fontFamily: "var(--font-heading)" }}>{z.name}</strong>
                  <span className="muted">{z.points.length} pts</span>
                </div>
                <button className="btn btn--danger btn--sm" aria-label={`Delete ${z.name}`} onClick={() => remove.mutate(z.id)}>
                  <Trash2 size={15} strokeWidth={1.5} />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function ZonePolygon({ zone }: { zone: Zone }) {
  const color = zone.kind === "alert" ? "var(--color-warning)" : "var(--color-destructive)";
  return (
    <polygon
      points={zone.points.map((p) => `${p[0]},${p[1]}`).join(" ")}
      fill={color}
      fillOpacity={0.18}
      stroke={color}
      strokeWidth={2}
      vectorEffect="non-scaling-stroke"
    />
  );
}

function round(n: number): number {
  return Math.round(Math.min(1, Math.max(0, n)) * 1000) / 1000;
}
