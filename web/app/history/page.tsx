"use client";

import { useEffect, useState } from "react";
import { DigestView } from "../components/DigestView";
import { Notice, PageHeader, PageScaffold } from "../components/UiPrimitives";
import { getDigestByDate } from "../../lib/api";
import type { Digest } from "../../lib/types";

export default function HistoryPage() {
  const [date, setDate] = useState(() => formatDateParam(new Date()));
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function searchDigest(targetDate = date) {
    setLoading(true);
    setError(null);
    try {
      setDigest(await getDigestByDate(targetDate));
    } catch (err) {
      setError(err instanceof Error ? err.message : "查询失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void searchDigest(formatDateParam(new Date()));
  }, []);

  return (
    <PageScaffold>
      <PageHeader
        eyebrow="历史简报"
        title="按日期查看简报快照"
        description="按自然日回看已经发布过的中文简报，适合复盘某一天的 AI 热点变化。"
        actions={
        <form
          className="inlineForm"
          onSubmit={(event) => {
            event.preventDefault();
            void searchDigest();
          }}
        >
          <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          <button type="submit">查询</button>
        </form>
        }
      />
      {loading ? <Notice>正在查询</Notice> : null}
      {error ? <Notice tone="danger">{error}</Notice> : null}
      {!loading && !error ? <DigestView digest={digest} /> : null}
    </PageScaffold>
  );
}

function formatDateParam(value: Date) {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}
