import type { ReactNode } from "react";

type PageScaffoldProps = {
  children: ReactNode;
  className?: string;
};

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  aside?: ReactNode;
  className?: string;
};

type SurfaceCardProps = {
  children: ReactNode;
  className?: string;
};

type CardHeaderProps = {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
};

type MetricCardProps = {
  label: string;
  value: ReactNode;
  helper?: ReactNode;
};

type NoticeProps = {
  tone?: "info" | "success" | "warning" | "danger";
  children: ReactNode;
  compact?: boolean;
};

export function PageScaffold({ children, className }: PageScaffoldProps) {
  return <main className={cx("pageSurface pageScaffold", className)}>{children}</main>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  aside,
  className
}: PageHeaderProps) {
  return (
    <section className={cx("pageHeader appPageHeader", className)}>
      <div className="pageTitleBlock">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        {description ? <p className="description">{description}</p> : null}
      </div>
      {aside ? <div className="pageHeaderAside">{aside}</div> : null}
      {actions ? <div className="pageHeaderActions">{actions}</div> : null}
    </section>
  );
}

export function SurfaceCard({ children, className }: SurfaceCardProps) {
  return <section className={cx("surfaceCard", className)}>{children}</section>;
}

export function CardHeader({ title, description, actions }: CardHeaderProps) {
  return (
    <div className="cardHeader">
      <div>
        <h2>{title}</h2>
        {description ? <p className="mutedText">{description}</p> : null}
      </div>
      {actions ? <div className="cardHeaderActions">{actions}</div> : null}
    </div>
  );
}

export function MetricCard({ label, value, helper }: MetricCardProps) {
  return (
    <div className="metricCard">
      <span>{label}</span>
      <strong>{value}</strong>
      {helper ? <small>{helper}</small> : null}
    </div>
  );
}

export function Notice({ tone = "info", compact = false, children }: NoticeProps) {
  return <section className={cx("notice", `notice-${tone}`, compact && "compact")}>{children}</section>;
}

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}
