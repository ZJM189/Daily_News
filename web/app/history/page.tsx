"use client";

import { useEffect, useState } from "react";
import { DigestView } from "../components/DigestView";
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
    <main className="pageSurface">
      <section className="toolbar">
        <div>
          <p className="eyebrow">历史简报</p>
          <h1>按日期查看简报快照</h1>
        </div>
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
      </section>
      {loading ? <section className="emptyState">正在查询</section> : null}
      {error ? <section className="errorState">{error}</section> : null}
      {!loading && !error ? <DigestView digest={digest} /> : null}
    </main>
  );
}

function formatDateParam(value: Date) {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}
