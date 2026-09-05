"use client";

import { useEffect, useState } from "react";
import { DigestView } from "../components/DigestView";
import { Notice, PageScaffold } from "../components/UiPrimitives";
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
    <PageScaffold>
      {loading ? <Notice>正在加载今日简报</Notice> : null}
      {error ? <Notice tone="danger">{error}</Notice> : null}
      {!loading && !error ? <DigestView digest={digest} /> : null}
    </PageScaffold>
  );
}
