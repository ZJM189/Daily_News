"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createSortedRowModel,
  createColumnHelper,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  sortFn_datetime,
  tableFeatures,
  useTable,
  type SortingState
} from "@tanstack/react-table";
import { PaginationBar } from "../../components/PaginationBar";
import {
  CardHeader,
  MetricCard,
  Notice,
  PageHeader,
  PageScaffold,
  SurfaceCard
} from "../../components/UiPrimitives";
import { apiPost, listJobs, triggerDailyPipelineJob } from "../../../lib/api";
import type { JobRun, PageMeta } from "../../../lib/types";

const jobActions = [
  { label: "抓取内容", path: "/api/v1/admin/jobs/collect", body: { source_types: [] } },
  { label: "整理内容", path: "/api/v1/admin/jobs/normalize", body: { limit: 5000 } },
  { label: "计算热度", path: "/api/v1/admin/jobs/rank", body: { limit: 500 } },
  { label: "合并相似内容", path: "/api/v1/admin/jobs/dedupe", body: { limit: 1000 } },
  { label: "生成中文摘要", path: "/api/v1/admin/jobs/summarize", body: { limit: 20, min_score: 70 } }
];

const jobTableFeatures = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: {
    alphanumeric: sortFn_alphanumeric,
    basic: sortFn_basic,
    datetime: sortFn_datetime
  }
});
const columnHelper = createColumnHelper<typeof jobTableFeatures, JobRun>();

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<JobRun[]>([]);
  const [meta, setMeta] = useState<PageMeta>({ page: 1, page_size: 20, total: 0 });
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);
  const [sorting, setSorting] = useState<SortingState>([]);

  const activeCount = jobs.filter((job) => job.status === "pending" || job.status === "running").length;
  const columns = useMemo(
    () =>
      columnHelper.columns([
      columnHelper.accessor("job_type", {
        id: "job_type",
        header: "任务",
        sortFn: "alphanumeric",
        cell: (info) => <JobName job={info.row.original} />
      }),
      columnHelper.accessor("status", {
        id: "status",
        header: "状态",
        sortFn: "alphanumeric",
        cell: (info) => (
          <span className={`statusBadge ${info.getValue()}`}>{statusLabel(info.getValue())}</span>
        )
      }),
      columnHelper.accessor((job) => job.success_count + job.failure_count, {
        id: "handled_count",
        header: "处理数量",
        sortFn: "basic",
        cell: (info) => <JobCount job={info.row.original} />
      }),
      columnHelper.accessor((job) => progressPercent(job), {
        id: "progress",
        header: "进度",
        sortFn: "basic",
        cell: (info) => <JobProgress job={info.row.original} />
      }),
      columnHelper.accessor("created_at", {
        id: "created_at",
        header: "创建时间",
        sortFn: "datetime",
        sortDescFirst: true,
        cell: (info) => formatDateTime(info.getValue())
      }),
      columnHelper.accessor((job) => durationSeconds(job), {
        id: "duration",
        header: "耗时",
        sortFn: "basic",
        cell: (info) => formatDuration(info.row.original)
      }),
      columnHelper.accessor("error_message", {
        id: "error_message",
        header: "说明/错误",
        sortFn: "alphanumeric",
        cell: (info) => <JobMessage value={info.getValue()} />
      })
    ]),
    []
  );
  const table = useTable({
    features: jobTableFeatures,
    data: jobs,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    enableSortingRemoval: true
  });

  async function refreshJobs(
    nextPage = meta.page,
    options: { silent?: boolean; pageSize?: number } = {}
  ) {
    const nextPageSize = options.pageSize ?? pageSize;
    if (options.silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    try {
      const result = await listJobs(nextPage, nextPageSize);
      setJobs(result.data);
      setMeta(result.meta);
      setPageSize(result.meta.page_size);
      setLastRefreshedAt(new Date());
    } finally {
      if (options.silent) {
        setRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  }

  async function handlePageSizeChange(nextPageSize: number) {
    setPageSize(nextPageSize);
    await refreshJobs(1, { pageSize: nextPageSize });
  }

  async function triggerJob(action: (typeof jobActions)[number]) {
    setRunningAction(action.label);
    setMessage(null);
    try {
      const createdJob = await apiPost<JobRun>(action.path, action.body);
      setJobs((currentJobs) => [createdJob, ...currentJobs.filter((job) => job.id !== createdJob.id)]);
      setMessage(`${action.label}任务已创建，后台会自动执行`);
      await refreshJobs(1);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setRunningAction(null);
    }
  }

  async function triggerDailyPipeline() {
    setRunningAction("一键生成今日简报");
    setMessage(null);
    try {
      const createdJobs = await triggerDailyPipelineJob();
      const createdJobIds = new Set(createdJobs.map((job) => job.id));
      setJobs((currentJobs) => [
        ...createdJobs,
        ...currentJobs.filter((job) => !createdJobIds.has(job.id))
      ]);
      setMessage(`今日简报流程已创建：${createdJobs.map((job) => jobTypeLabel(job.job_type)).join(" → ")}`);
      await refreshJobs(1);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setRunningAction(null);
    }
  }

  async function triggerDigest() {
    const today = formatDateParam(new Date());
    setRunningAction("发布今日简报");
    setMessage(null);
    try {
      const createdJob = await apiPost<JobRun>("/api/v1/admin/jobs/generate-digest", { digest_date: today });
      setJobs((currentJobs) => [createdJob, ...currentJobs.filter((job) => job.id !== createdJob.id)]);
      setMessage("发布今日简报任务已创建，后台会自动执行");
      await refreshJobs(1);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setRunningAction(null);
    }
  }

  useEffect(() => {
    void refreshJobs(1);
  }, []);

  useEffect(() => {
    if (activeCount === 0) {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshJobs(meta.page, { silent: true });
    }, 3000);

    return () => window.clearInterval(timer);
  }, [activeCount, meta.page, pageSize]);

  return (
    <PageScaffold>
      <PageHeader
        eyebrow="管理员"
        title="任务日志"
        description="查看采集和简报生成进度。存在等待或运行任务时，页面会每 3 秒自动刷新。"
        actions={
          <div className="toolbarActions">
          <span className="mutedText">
            {refreshing ? "刷新中" : lastRefreshedAt ? `最近刷新 ${formatTime(lastRefreshedAt)}` : ""}
          </span>
          <button type="button" disabled={runningAction !== null} onClick={() => void triggerDailyPipeline()}>
            {runningAction === "一键生成今日简报" ? "创建中" : "一键生成今日简报"}
          </button>
          <button className="ghostButton" type="button" onClick={() => void refreshJobs(meta.page)}>
            刷新
          </button>
        </div>
        }
      />

      <section className="workflowGuide">
        <div>
          <strong>1. 抓取内容</strong>
          <span>从已启用来源拉取最新信息</span>
        </div>
        <div>
          <strong>2. 整理内容</strong>
          <span>清洗标题、去重并统一字段</span>
        </div>
        <div>
          <strong>3. 计算热度</strong>
          <span>按来源、时间和关键词打分</span>
        </div>
        <div>
          <strong>4. 合并相似内容</strong>
          <span>把同一事件或项目聚成专题</span>
        </div>
        <div>
          <strong>5. 生成摘要</strong>
          <span>为候选内容生成中文摘要</span>
        </div>
        <div>
          <strong>6. 发布简报</strong>
          <span>按日期写入今日简报</span>
        </div>
      </section>

      <SurfaceCard className="manualJobPanel">
        <CardHeader
          title="单步重跑（高级）"
          description="通常直接使用“一键生成今日简报”。下面按钮用于排查或补跑某个环节。"
        />
        <div className="actionBar compactActionBar">
          {jobActions.map((action) => (
            <button
              key={action.path}
              type="button"
              disabled={runningAction !== null}
              onClick={() => void triggerJob(action)}
            >
              {runningAction === action.label ? "创建中" : action.label}
            </button>
          ))}
          <button type="button" disabled={runningAction !== null} onClick={() => void triggerDigest()}>
            {runningAction === "发布今日简报" ? "创建中" : "发布今日简报"}
          </button>
        </div>
      </SurfaceCard>

      {message ? <Notice tone="success">{message}</Notice> : null}

      <section className="metricStrip jobSummaryGrid">
        <MetricCard label="任务总数" value={meta.total} />
        <MetricCard label="本页等待" value={jobs.filter((job) => job.status === "pending").length} />
        <MetricCard label="本页运行" value={jobs.filter((job) => job.status === "running").length} />
        <MetricCard
          label="本页异常"
          value={jobs.filter((job) => job.status === "failed" || job.status === "partial_success").length}
        />
      </section>

      <SurfaceCard className="tableCard">
        <CardHeader
          title="任务记录"
          description="点击表头可按当前页排序，运行中的任务会自动刷新。"
        />
        <div className="tableWrap jobTableWrap">
          {loading ? (
            <div className="emptyState">正在加载任务</div>
          ) : table.getRowModel().rows.length === 0 ? (
            <div className="emptyState">暂无任务日志。</div>
          ) : (
            <table className="dataTable jobDataTable">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className={`jobHeader ${header.column.id}`}>
                      {header.isPlaceholder ? null : (
                        <button
                          className="tableSortButton"
                          type="button"
                          disabled={!header.column.getCanSort()}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          <span>
                            <table.FlexRender header={header} />
                          </span>
                          {header.column.getCanSort() ? (
                            <span className="sortIndicator">{sortIndicator(header.column.getIsSorted())}</span>
                          ) : null}
                        </button>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id}>
                  {row.getAllCells().map((cell) => (
                    <td key={cell.id} className={`jobCell ${cell.column.id}`}>
                      <table.FlexRender cell={cell} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
            </table>
          )}
        </div>
      </SurfaceCard>
      <PaginationBar
        meta={meta}
        loading={loading || refreshing}
        onPageChange={(nextPage) => refreshJobs(nextPage)}
        onPageSizeChange={handlePageSizeChange}
      />
    </PageScaffold>
  );
}

function JobName({ job }: { job: JobRun }) {
  return (
    <div className="jobNameCell">
      <strong>{jobTypeLabel(job.job_type)}</strong>
      <span>{job.trigger_type} · {job.id.slice(0, 8)}</span>
    </div>
  );
}

function JobCount({ job }: { job: JobRun }) {
  return (
    <div className="jobCountCell">
      <strong>
        {job.success_count}/{job.total_count || "-"}
      </strong>
      {job.failure_count ? <span>失败 {job.failure_count}</span> : <span>失败 0</span>}
    </div>
  );
}

function JobMessage({ value }: { value: string | null }) {
  if (!value) {
    return <span className="mutedText">-</span>;
  }

  const summary = value.length > 56 ? `${value.slice(0, 56)}...` : value;
  return (
    <details className="jobMessageCell">
      <summary>{summary}</summary>
      <p>{value}</p>
    </details>
  );
}

function JobProgress({ job }: { job: JobRun }) {
  const percent = progressPercent(job);
  const isActive = job.status === "pending" || job.status === "running";

  return (
    <div className="jobProgressCell">
      <div className={`progressTrack ${isActive && job.total_count === 0 ? "indeterminate" : ""}`}>
        <span style={{ width: `${percent}%` }} />
      </div>
      <span className="mutedText">
        {job.status === "pending"
          ? "等待后台执行"
          : job.status === "running" && job.total_count === 0
            ? "执行中"
            : `${percent}%`}
      </span>
    </div>
  );
}

function progressPercent(job: JobRun) {
  const completedCount = job.success_count + job.failure_count;
  return job.total_count > 0 ? Math.min(100, Math.round((completedCount / job.total_count) * 100)) : 0;
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: "等待中",
    running: "运行中",
    success: "成功",
    failed: "失败",
    partial_success: "部分成功",
    cancelled: "已取消"
  };
  return labels[status] ?? status;
}

function jobTypeLabel(jobType: string) {
  const labels: Record<string, string> = {
    collect: "抓取内容",
    normalize: "整理内容",
    rank: "计算热度",
    dedupe: "合并相似内容",
    summarize: "生成中文摘要",
    generate_digest: "发布今日简报",
    publish_digest: "发布简报"
  };
  return labels[jobType] ?? jobType;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function formatDateParam(value: Date) {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatTime(value: Date) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(value);
}

function formatDuration(job: JobRun) {
  const seconds = durationSeconds(job);
  if (job.status === "pending") {
    return "-";
  }
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}

function durationSeconds(job: JobRun) {
  const start = job.started_at ? new Date(job.started_at) : new Date(job.created_at);
  const end = job.ended_at ? new Date(job.ended_at) : new Date();
  return Math.max(0, Math.round((end.getTime() - start.getTime()) / 1000));
}

function sortIndicator(value: false | "asc" | "desc") {
  if (value === "asc") {
    return "↑";
  }
  if (value === "desc") {
    return "↓";
  }
  return "↕";
}
