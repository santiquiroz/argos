import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Radar } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { CameraTile } from "../components/CameraTile";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState, Spinner } from "../components/ui/Feedback";

export function Live() {
  const qc = useQueryClient();
  const cameras = useQuery({ queryKey: ["cameras"], queryFn: api.cameras });
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");

  const add = useMutation({
    mutationFn: () => api.addCamera(name, url),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cameras"] });
      setAdding(false);
      setName("");
      setUrl("");
    },
  });
  const remove = useMutation({
    mutationFn: (n: string) => api.removeCamera(n),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cameras"] }),
  });

  if (cameras.isLoading) return <Spinner />;
  const list = cameras.data ?? [];

  return (
    <div className="stack">
      <div className="between">
        <span className="muted">{list.length} camera(s) · sub-stream MJPEG</span>
        <div className="page-actions">
          <Link to="/discovery" className="btn btn--secondary btn--sm">
            <Radar size={16} strokeWidth={1.5} /> Discover
          </Link>
          <Button small onClick={() => setAdding((v) => !v)}>
            <Plus size={16} strokeWidth={1.5} /> Add camera
          </Button>
        </div>
      </div>

      {adding && (
        <Card title="Add camera">
          <div className="row" style={{ alignItems: "flex-end", gap: 12, flexWrap: "wrap" }}>
            <div className="field" style={{ flex: "0 0 160px" }}>
              <label className="field__label">Name</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="front" />
            </div>
            <div className="field" style={{ flex: 1, minWidth: 280 }}>
              <label className="field__label">RTSP URL (sub-stream …02)</label>
              <input
                className="input"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="rtsp://admin:pass@192.168.1.10:554/Streaming/Channels/102"
              />
            </div>
            <Button onClick={() => add.mutate()} disabled={!name || !url || add.isPending}>
              {add.isPending ? "Adding…" : "Add"}
            </Button>
          </div>
        </Card>
      )}

      {list.length === 0 ? (
        <Card>
          <EmptyState>
            No cameras yet. <Link to="/discovery" style={{ color: "var(--color-accent)" }}>Discover</Link> them on your
            network, or add one manually.
          </EmptyState>
        </Card>
      ) : (
        <div className="grid grid--cameras">
          {list.map((c) => (
            <CameraTile key={c.name} name={c.name} onRemove={() => remove.mutate(c.name)} />
          ))}
        </div>
      )}
    </div>
  );
}
