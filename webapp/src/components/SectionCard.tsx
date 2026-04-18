"use client";
interface Props {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  id?: string;
}

export default function SectionCard({ title, subtitle, children, className = "", id }: Props) {
  return (
    <div id={id} className={`card ${className}`}>
      {title && (
        <div className="mb-5">
          <h3 className="text-sm font-700 uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
            {title}
          </h3>
          {subtitle && <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{subtitle}</p>}
          <div className="mt-3 h-px" style={{ background: "var(--border)" }} />
        </div>
      )}
      {children}
    </div>
  );
}
