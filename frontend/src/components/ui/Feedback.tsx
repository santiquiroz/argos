import { ReactNode } from "react";

export function Badge({ children, variant }: { children: ReactNode; variant?: "live" | "warning" | "danger" }) {
  return <span className={`badge ${variant ? `badge--${variant}` : ""}`}>{children}</span>;
}

export function Dot({ variant }: { variant?: "live" | "warning" | "danger" }) {
  return <span className={`dot ${variant ? `dot--${variant}` : ""}`} />;
}

export function Spinner() {
  return <span className="spinner" role="status" aria-label="loading" />;
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
