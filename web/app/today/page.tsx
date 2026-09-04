"use client";

import { useEffect, useState } from "react";
import { DigestView } from "../components/DigestView";
import { getTodayDigest } from "../../lib/api";
import type { Digest } from "../../lib/types";

export default function TodayPage() {
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTodayDigest()
      .then(setDigest)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="pageSurface">
      {loading ? <section className="emptyState">正在加载今日简报</section> : null}
      {error ? <section className="errorState">{error}</section> : null}
      {!loading && !error ? <DigestView digest={digest} /> : null}
    </main>
  );
}
