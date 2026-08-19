import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Camera, Clock } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, observationThumbUrl, personThumbUrl } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge, EmptyState, Spinner } from "../components/ui/Feedback";
import { relativeTime } from "../lib/useLiveEvents";

export function PersonDetail() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const detail = useQuery({ queryKey: ["person", id], queryFn: () => api.person(id) });
  const [name, setName] = useState("");
  const enroll = useMutation({
    mutationFn: () => api.enroll(id, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["person", id] });
      qc.invalidateQueries({ queryKey: ["persons"] });
    },
  });

  if (detail.isLoading || !detail.data) return <Spinner />;
  const { person, observations, cameras } = detail.data;

  return (
    <div className="stack">
      <Link to="/persons" className="row muted" style={{ fontSize: 14 }}>
        <ArrowLeft size={16} strokeWidth={1.5} /> Persons
      </Link>

      <Card>
        <div className="row" style={{ gap: 16, alignItems: "flex-start" }}>
          <img className="avatar" style={{ width: 72, height: 72 }} src={personThumbUrl(id)} alt="" />
          <div className="stack" style={{ gap: 8, flex: 1 }}>
            <div className="between">
              <h2 style={{ fontSize: 22 }}>{person.name ?? `#${person.id.slice(0, 8)}`}</h2>
              {person.enrolled ? <Badge variant="live">enrolled</Badge> : <Badge>anonymous</Badge>}
            </div>
            <div className="row" style={{ gap: 16, flexWrap: "wrap" }}>
              <span className="muted"><Camera size={14} strokeWidth={1.5} /> {cameras.join(", ") || "—"}</span>
              <span className="muted"><Clock size={14} strokeWidth={1.5} /> last seen {relativeTime(person.last_seen)}</span>
              <span className="muted">{observations.length} observation(s)</span>
            </div>
            {!person.enrolled && (
              <div className="row" style={{ marginTop: 4 }}>
                <input className="input" style={{ height: 38, width: 180 }} placeholder="name this person…" value={name} onChange={(e) => setName(e.target.value)} />
                <Button small onClick={() => enroll.mutate()} disabled={!name || enroll.isPending}>Enroll</Button>
              </div>
            )}
          </div>
        </div>
      </Card>

      <Card title="Timeline">
        {observations.length === 0 ? (
          <EmptyState>No observations recorded yet.</EmptyState>
        ) : (
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))" }}>
            {observations.map((o) => (
              <figure key={o.id} style={{ margin: 0 }}>
                <img
                  src={observationThumbUrl(o.id)}
                  alt=""
                  style={{ width: "100%", aspectRatio: "3/4", objectFit: "cover", borderRadius: 8, border: "1px solid var(--color-border)", background: "var(--color-muted)" }}
                  onError={(e) => ((e.target as HTMLImageElement).style.visibility = "hidden")}
                />
                <figcaption className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                  {o.camera} · {relativeTime(o.ts)}
                </figcaption>
              </figure>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
