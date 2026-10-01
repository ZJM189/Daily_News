import type { VisitStats } from "../../lib/types";

export function AppFooter({ visitStats }: { visitStats?: VisitStats | null }) {
  return (
    <footer className="appFooter" aria-label="版权信息">
      <span className="appFooterCopy">© 2026 Jimmy Zhang. Daily AI News.</span>
      {visitStats ? (
        <div className="appFooterStats" aria-label="站点访问统计">
          <span>累计访问 <strong>{visitStats.total_visits}</strong></span>
          <span>今日访问 <strong>{visitStats.today_visits}</strong></span>
          <span>访客数 <strong>{visitStats.unique_visitors}</strong></span>
        </div>
      ) : null}
    </footer>
  );
}
