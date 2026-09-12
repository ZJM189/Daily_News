export default function RadarMark({ className = "" }: { className?: string }) {
  return (
    <span className={["radarMark", className].filter(Boolean).join(" ")} aria-hidden="true">
      <span className="radarMarkBlip" />
    </span>
  );
}
