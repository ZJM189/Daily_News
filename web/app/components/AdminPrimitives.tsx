import type { ReactNode } from "react";

type AdminMetricProps = {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  detail: ReactNode;
  tone?: "default" | "success" | "warning" | "danger";
};

type AdminStatusBadgeProps = {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
};

export function AdminMetric({
  icon,
  label,
  value,
  detail,
  tone = "default"
}: AdminMetricProps) {
  return (
    <div className={`managementMetric tone-${tone}`}>
      <span className="managementMetricIcon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
    </div>
  );
}

export function AdminStatusBadge({ children, tone = "neutral" }: AdminStatusBadgeProps) {
  return (
    <span className={`managementStatusBadge tone-${tone}`}>
      <span className="managementStatusDot" aria-hidden="true" />
      {children}
    </span>
  );
}

export function AdminEmptyState({
  icon,
  title,
  description
}: {
  icon: ReactNode;
  title: string;
  description?: string;
}) {
  return (
    <div className="managementEmptyState">
      <span aria-hidden="true">{icon}</span>
      <strong>{title}</strong>
      {description ? <span>{description}</span> : null}
    </div>
  );
}
