import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserRound } from "lucide-react";
import { useState } from "react";
import { api, Person } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge, EmptyState, Spinner } from "../components/ui/Feedback";
import { relativeTime } from "../lib/useLiveEvents";

export function Persons() {
  const persons = useQuery({ queryKey: ["persons"], queryFn: api.persons, refetchInterval: 10000 });
  if (persons.isLoading) return <Spinner />;
  const list = persons.data ?? [];

  return (
    <Card title={`Persons (${list.length})`}>
      {list.length === 0 ? (
        <EmptyState>No persons yet. Once cameras are running, detected people appear here as anonymous clusters you can name.</EmptyState>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Identity</th>
              <th>Status</th>
              <th>Last seen</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {list.map((p) => (
              <PersonRow key={p.id} person={p} />
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function PersonRow({ person }: { person: Person }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const enroll = useMutation({
    mutationFn: () => api.enroll(person.id, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["persons"] }),
  });

  return (
    <tr>
      <td>
        <div className="row">
          <UserRound size={18} strokeWidth={1.5} color="var(--color-muted-foreground)" />
          {person.name ?? <span className="muted">#{person.id.slice(0, 8)}</span>}
        </div>
      </td>
      <td>
        {person.enrolled ? <Badge variant="live">enrolled</Badge> : <Badge>anonymous</Badge>}
      </td>
      <td className="muted">{relativeTime(person.last_seen)}</td>
      <td>
        {!person.enrolled && (
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <input className="input" style={{ height: 36, width: 140 }} placeholder="name…" value={name} onChange={(e) => setName(e.target.value)} />
            <Button small onClick={() => enroll.mutate()} disabled={!name || enroll.isPending}>
              Enroll
            </Button>
          </div>
        )}
      </td>
    </tr>
  );
}
