"use client";

import { useEffect, useState } from "react";
import { getCurrentUser, getTodayDigest } from "../../lib/api";
import type { Digest } from "../../lib/types";
import { DigestView } from "./DigestView";
import { Notice, PageScaffold } from "./UiPrimitives";

export function TodayDigestPage() {
  const [digest, setDigest] = useState<Digest | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      getTodayDigest(),
      getCurrentUser()
        .then(() => true)
        .catch(() => false)
    ])
      .then(([nextDigest, hasUser]) => {
        if (!active) return;
        setDigest(nextDigest);
        setAuthenticated(hasUser);
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const mode = authenticated ? "workspace" : "public";

  return (
    <PageScaffold className={authenticated ? undefined : "publicBriefingPage"}>
      {loading ? <Notice>正在加载今日简报</Notice> : null}
      {error ? <Notice tone="danger">{error}</Notice> : null}
      {!loading && !error ? <DigestView digest={digest} mode={mode} /> : null}
    </PageScaffold>
  );
}
