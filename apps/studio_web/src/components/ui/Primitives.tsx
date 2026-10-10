import type { PropsWithChildren, ReactNode } from "react";

export function Card({ children, title, action }: PropsWithChildren<{ title?: string; action?: ReactNode }>) {
  return (
    <section className="card">
      {(title || action) && (
        <header className="card-header">
          {title ? <h2 className="card-title">{title}</h2> : <span />}
          {action}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  );
}

export function Button({ children, variant = "secondary", ...props }: PropsWithChildren<{
  variant?: "primary" | "secondary" | "danger";
} & React.ButtonHTMLAttributes<HTMLButtonElement>>) {
  const variantClass = variant === "primary" ? "btn-primary" : variant === "danger" ? "btn-danger" : "";
  return <button {...props} className={`btn ${variantClass} ${props.className ?? ""}`}>{children}</button>;
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`input ${props.className ?? ""}`} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`select ${props.className ?? ""}`} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`textarea ${props.className ?? ""}`} />;
}

export function Field({ label, children }: PropsWithChildren<{ label: string }>) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty-state">
      <div className="empty-title">{title}</div>
      <div className="empty-body">{body}</div>
    </div>
  );
}

export function StatusPill({ children, tone = "neutral" }: PropsWithChildren<{ tone?: "neutral" | "ok" | "warn" }>) {
  const toneClass = tone === "ok" ? "status-ok" : tone === "warn" ? "status-warn" : "";
  return <span className={`status-pill ${toneClass}`}>{children}</span>;
}
