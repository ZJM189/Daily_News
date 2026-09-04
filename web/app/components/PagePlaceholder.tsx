export function PagePlaceholder({
  title,
  description,
  actions
}: {
  title: string;
  description: string;
  actions?: string[];
}) {
  return (
    <main className="pageSurface">
      <section className="pageHeader">
        <div>
          <p className="eyebrow">建设中</p>
          <h1>{title}</h1>
          <p className="description">{description}</p>
        </div>
      </section>
      {actions ? (
        <section className="roadmapList">
          {actions.map((action) => (
            <div key={action} className="roadmapItem">
              {action}
            </div>
          ))}
        </section>
      ) : null}
    </main>
  );
}
