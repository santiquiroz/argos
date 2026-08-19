import { Trash2, VideoOff } from "lucide-react";
import { useState } from "react";
import { mjpegUrl } from "../lib/api";
import { Badge } from "./ui/Feedback";

export function CameraTile({ name, onRemove }: { name: string; onRemove?: () => void }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className="camera">
      {failed ? (
        <div className="camera__video" style={{ display: "grid", placeItems: "center", color: "#64748b" }}>
          <div className="stack" style={{ alignItems: "center", gap: 8 }}>
            <VideoOff size={28} strokeWidth={1.5} />
            <span style={{ fontSize: 13 }}>stream unavailable</span>
          </div>
        </div>
      ) : (
        <img
          className="camera__video"
          src={mjpegUrl(name)}
          alt={`Live view of ${name}`}
          onError={() => setFailed(true)}
        />
      )}
      <div className="camera__bar">
        <span className="camera__name">{name}</span>
        <div className="row">
          <Badge variant={failed ? "danger" : "live"}>{failed ? "offline" : "live"}</Badge>
          {onRemove && (
            <button className="btn btn--danger btn--sm" aria-label={`Remove ${name}`} onClick={onRemove}>
              <Trash2 size={15} strokeWidth={1.5} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
