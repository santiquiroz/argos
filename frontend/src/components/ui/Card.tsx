import { ReactNode } from "react";

export function Card({ title, actions, children, className = "" }: { title?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="between" style={{ marginBottom: title ? 0 : undefined }}>
          {title && <div className="card__title" style={{ marginBottom: 0 }}>{title}</div>}
          {actions}
        </div>
      )}
      <div style={{ marginTop: title || actions ? 16 : 0 }}>{children}</div>
    </section>
  );
}

export function Stat({ value, label }: { value: ReactNode; label: string }) {
  return (
    <section className="card">
      <div className="stat__value">{value}</div>
      <div className="stat__label">{label}</div>
    </section>
  );
}
