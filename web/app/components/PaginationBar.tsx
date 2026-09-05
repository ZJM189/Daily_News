"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { PageMeta } from "../../lib/types";

type PageMarker = number | "ellipsis-left" | "ellipsis-right";

type PaginationBarProps = {
  meta: PageMeta;
  loading?: boolean;
  onPageChange: (page: number) => void | Promise<void>;
  pageSizeOptions?: number[];
  onPageSizeChange?: (pageSize: number) => void | Promise<void>;
};

const defaultPageSizeOptions = [10, 20, 50, 100];

export function PaginationBar({
  meta,
  loading = false,
  onPageChange,
  pageSizeOptions = defaultPageSizeOptions,
  onPageSizeChange
}: PaginationBarProps) {
  const totalPages = Math.max(1, Math.ceil(meta.total / Math.max(meta.page_size, 1)));
  const currentPage = clampPage(meta.page, totalPages);
  const [draftPage, setDraftPage] = useState(String(currentPage));
  const pages = useMemo(() => visiblePages(currentPage, totalPages), [currentPage, totalPages]);

  useEffect(() => {
    setDraftPage(String(currentPage));
  }, [currentPage]);

  function goToPage(nextPage: number) {
    const targetPage = clampPage(nextPage, totalPages);
    if (loading || targetPage === currentPage) {
      return;
    }
    void onPageChange(targetPage);
  }

  function handleJump(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const targetPage = Number.parseInt(draftPage, 10);
    if (!Number.isFinite(targetPage)) {
      setDraftPage(String(currentPage));
      return;
    }
    goToPage(targetPage);
  }

  function handlePageSizeChange(value: string) {
    const nextPageSize = Number.parseInt(value, 10);
    if (!Number.isFinite(nextPageSize) || nextPageSize === meta.page_size || !onPageSizeChange) {
      return;
    }
    void onPageSizeChange(nextPageSize);
  }

  return (
    <nav className="paginationBar" aria-label="分页导航">
      <div className="paginationInfo">
        <strong>共 {meta.total} 条</strong>
        <label className="paginationSize">
          <span>每页</span>
          <select
            value={meta.page_size}
            disabled={loading || !onPageSizeChange}
            onChange={(event) => handlePageSizeChange(event.target.value)}
            aria-label="选择每页展示数量"
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <span>条</span>
        </label>
      </div>

      <div className="paginationPages">
        <button
          className="ghostButton"
          type="button"
          disabled={loading || currentPage <= 1}
          onClick={() => goToPage(1)}
        >
          首页
        </button>
        <button
          className="ghostButton"
          type="button"
          disabled={loading || currentPage <= 1}
          onClick={() => goToPage(currentPage - 1)}
        >
          上一页
        </button>
        {pages.map((page) =>
          typeof page === "number" ? (
            <button
              key={page}
              className={`ghostButton paginationPage ${page === currentPage ? "active" : ""}`}
              type="button"
              disabled={loading || page === currentPage}
              aria-current={page === currentPage ? "page" : undefined}
              onClick={() => goToPage(page)}
            >
              {page}
            </button>
          ) : (
            <span key={page} className="paginationEllipsis" aria-hidden="true">
              ...
            </span>
          )
        )}
        <button
          className="ghostButton"
          type="button"
          disabled={loading || currentPage >= totalPages}
          onClick={() => goToPage(currentPage + 1)}
        >
          下一页
        </button>
        <button
          className="ghostButton"
          type="button"
          disabled={loading || currentPage >= totalPages}
          onClick={() => goToPage(totalPages)}
        >
          末页
        </button>
      </div>

      <form className="paginationJump" onSubmit={handleJump}>
        <span className="paginationCurrent">
          第 {currentPage} / {totalPages} 页
        </span>
        <label>
          <span>跳转到</span>
          <input
            type="number"
            min="1"
            max={totalPages}
            value={draftPage}
            disabled={loading || totalPages <= 1}
            onChange={(event) => setDraftPage(event.target.value)}
            aria-label="输入页码"
          />
          <span>页</span>
        </label>
        <button className="ghostButton" type="submit" disabled={loading || totalPages <= 1}>
          确定
        </button>
      </form>
    </nav>
  );
}

function visiblePages(currentPage: number, totalPages: number): PageMarker[] {
  if (totalPages <= 7) {
    return range(1, totalPages);
  }

  let start = Math.max(2, currentPage - 1);
  let end = Math.min(totalPages - 1, currentPage + 1);

  if (currentPage <= 4) {
    start = 2;
    end = 5;
  }
  if (currentPage >= totalPages - 3) {
    start = totalPages - 4;
    end = totalPages - 1;
  }

  const pages: PageMarker[] = [1];
  if (start > 2) {
    pages.push("ellipsis-left");
  }
  pages.push(...range(start, end));
  if (end < totalPages - 1) {
    pages.push("ellipsis-right");
  }
  pages.push(totalPages);
  return pages;
}

function range(start: number, end: number) {
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}

function clampPage(page: number, totalPages: number) {
  if (!Number.isFinite(page)) {
    return 1;
  }
  return Math.min(Math.max(Math.trunc(page), 1), totalPages);
}
