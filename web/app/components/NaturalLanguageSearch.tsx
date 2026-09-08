"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ArrowUpRight, Bot, LoaderCircle, Search, Sparkles, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { naturalLanguageLibrarySearch } from "../../lib/api";
import type { NaturalLanguageLibrarySearch } from "../../lib/types";

const EXAMPLE_QUERIES = ["最近 7 天 RAG 论文", "GitHub 上 80 分以上的项目"];

export function NaturalLanguageSearch() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<NaturalLanguageLibrarySearch | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  async function submit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const cleanedQuery = query.trim();
    if (!cleanedQuery || loading) return;

    await runQuery(cleanedQuery);
  }

  async function runQuery(nextQuery: string) {
    setLoading(true);
    setError(null);
    try {
      setResult(await naturalLanguageLibrarySearch(nextQuery));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "智能查询失败");
    } finally {
      setLoading(false);
    }
  }

  function close() {
    setOpen(false);
    setError(null);
  }

  return (
    <>
      {open ? (
        <section className="naturalSearchPanel" role="dialog" aria-modal="false" aria-label="智能查询">
          <div className="naturalSearchHeader">
            <div className="naturalSearchTitle">
              <span className="naturalSearchIcon" aria-hidden="true">
                <Sparkles size={17} />
              </span>
              <div>
                <h2>智能查询</h2>
                <p>查询已入库内容</p>
              </div>
            </div>
            <button className="iconButton" type="button" aria-label="关闭智能查询" title="关闭" onClick={close}>
              <X size={18} />
            </button>
          </div>

          <form className="naturalSearchForm" onSubmit={(event) => void submit(event)}>
            <div className="naturalSearchInputWrap">
              <Search size={17} aria-hidden="true" />
              <input
                ref={inputRef}
                aria-label="自然语言查询"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="例如：最近 7 天的 RAG 论文"
                maxLength={200}
              />
              <button
                className="naturalSearchSubmit"
                type="submit"
                aria-label="执行智能查询"
                title="执行查询"
                disabled={!query.trim() || loading}
              >
                {loading ? <LoaderCircle className="spin" size={17} /> : <ArrowUpRight size={17} />}
              </button>
            </div>
          </form>

          {!result && !loading && !error ? (
            <div className="naturalSearchExamples">
              {EXAMPLE_QUERIES.map((example) => (
                <button
                  className="naturalSearchExample"
                  type="button"
                  key={example}
                  onClick={() => {
                    setQuery(example);
                    void runQuery(example);
                  }}
                >
                  {example}
                </button>
              ))}
            </div>
          ) : null}

          {loading ? <div className="naturalSearchLoading">正在理解查询并检索信息库</div> : null}
          {error ? <div className="naturalSearchError" role="alert">{error}</div> : null}
          {result ? <SearchResults result={result} onOpenLibrary={() => router.push(result.library_url)} /> : null}
        </section>
      ) : (
        <button
          className="naturalSearchTrigger"
          type="button"
          aria-label="打开智能查询"
          onClick={() => setOpen(true)}
        >
          <Sparkles size={18} aria-hidden="true" />
          <span>智能查询</span>
        </button>
      )}
    </>
  );
}

function SearchResults({
  result,
  onOpenLibrary
}: {
  result: NaturalLanguageLibrarySearch;
  onOpenLibrary: () => void;
}) {
  return (
    <div className="naturalSearchResults">
      <div className="naturalSearchResultSummary">
        <div>
          <span className={`naturalSearchMode ${result.mode}`}>
            <Bot size={14} aria-hidden="true" />
            {result.mode === "llm" ? "智能解析" : "关键词兜底"}
          </span>
          <p>{result.explanation}</p>
        </div>
        {result.llm ? <strong>{Math.round(result.llm.confidence * 100)}% 匹配</strong> : null}
      </div>

      {result.chips.length ? (
        <div className="naturalSearchChips">
          {result.chips.map((chip) => <span key={chip.key}>{chip.label}</span>)}
        </div>
      ) : null}

      {result.data.length ? (
        <div className="naturalSearchItemList">
          {result.data.map((item) => (
            <a className="naturalSearchItem" key={item.id} href={item.url} target="_blank" rel="noreferrer">
              <strong>{item.title}</strong>
              <span>{item.source.name} · {item.score.toFixed(1)} 分</span>
            </a>
          ))}
        </div>
      ) : (
        <div className="naturalSearchEmpty">没有找到匹配的已入库内容</div>
      )}

      <button className="naturalSearchLibraryLink" type="button" onClick={onOpenLibrary}>
        在信息库查看全部
        <ArrowUpRight size={16} aria-hidden="true" />
      </button>
    </div>
  );
}
