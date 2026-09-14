"use client";

import { useEffect, useState } from "react";
import { getCurrentUser, getPublicDigestByDate, getTodayDigest } from "../../lib/api";
import type { Digest } from "../../lib/types";
import { DigestView } from "./DigestView";
import { Notice, PageScaffold } from "./UiPrimitives";

export function TodayDigestPage() {
  const [selectedDate, setSelectedDate] = useState(() => todayInShanghai());
  const [digest, setDigest] = useState<Digest | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDigest(targetDate: string) {
    setLoading(true);
    setError(null);
    try {
      const today = todayInShanghai();
      const digestRequest =
        targetDate === today ? getTodayDigest() : getPublicDigestByDate(targetDate);
      const [nextDigest, hasUser] = await Promise.all([
        digestRequest,
        getCurrentUser()
          .then(() => true)
          .catch(() => false)
      ]);
      setDigest(nextDigest);
      setAuthenticated(hasUser);
    } catch (err) {
      setError(err instanceof Error ? err.message : "查询失败");
    } finally {
      setLoading(false);
    }
  }

  function handleDigestDateChange(targetDate: string) {
    setSelectedDate(targetDate);
    void loadDigest(targetDate);
  }

  useEffect(() => {
    let active = true;
    const initialDate = todayInShanghai();
    Promise.all([
      getTodayDigest(),
      getCurrentUser()
        .then(() => true)
        .catch(() => false)
    ])
      .then(([nextDigest, hasUser]) => {
        if (!active) return;
        setSelectedDate(initialDate);
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
      {loading ? <Notice>正在加载今日 AI 简报</Notice> : null}
      {error ? <Notice tone="danger">{error}</Notice> : null}
      {!loading && !error ? (
        <DigestView
          digest={digest}
          mode={mode}
          selectedDate={selectedDate}
          maxDate={todayInShanghai()}
          onDigestDateChange={mode === "public" ? handleDigestDateChange : undefined}
        />
      ) : null}
    </PageScaffold>
  );
}

function todayInShanghai() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(new Date());
}
