"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  Clock3,
  ListChecks,
  Play,
  RefreshCw,
  Search,
  TerminalSquare,
  WandSparkles
} from "lucide-react";
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
import {
  AdminEmptyState,
  AdminMetric,
  AdminStatusBadge
} from "../../components/AdminPrimitives";
import { Modal } from "../../components/Modal";
import { PaginationBar } from "../../components/PaginationBar";
import { Notice, PageHeader, PageScaffold } from "../../components/UiPrimitives";
import { apiPost, listJobs, triggerDailyPipelineJob } from "../../../lib/api";
import type { JobRun, PageMeta } from "../../../lib/types";

const jobActions = [
  { label: "抓取内容", description: "从全部启用来源拉取最新信息", path: "/api/v1/admin/jobs/collect", body: { source_types: [] } },
  { label: "整理内容", description: "清洗并统一待处理内容字段", path: "/api/v1/admin/jobs/normalize", body: { limit: 5000 } },
  { label: "计算热度", description: "重新计算候选内容分数", path: "/api/v1/admin/jobs/rank", body: { limit: 500 } },
  { label: "合并相似内容", description: "合并重复内容并生成专题", path: "/api/v1/admin/jobs/dedupe", body: { limit: 1000 } },
  { label: "生成中文摘要", description: "为高分候选内容生成摘要", path: "/api/v1/admin/jobs/summarize", body: { limit: 20, min_score: 70 } }
];

const pipelineSteps = ["抓取内容", "整理内容", "计算热度", "合并相似内容", "生成摘要", "发布简报"];
const jobTypes = ["collect", "normalize", "rank", "dedupe", "summarize", "generate_digest", "publish_digest"];

const jobTableFeatures = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric, basic: sortFn_basic, datetime: sortFn_datetime }
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
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [commandOpen, setCommandOpen] = useState(false);

  const activeCount = jobs.filter((job) => job.status === "pending" || job.status === "running").length;
  const successCount = jobs.filter((job) => job.status === "success").length;
  const abnormalCount = jobs.filter((job) => job.status === "failed" || job.status === "partial_success").length;
  const filteredJobs = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return jobs.filter((job) => {
      const matchesKeyword =
        !keyword ||
        jobTypeLabel(job.job_type).toLowerCase().includes(keyword) ||
        job.job_type.toLowerCase().includes(keyword) ||
        job.id.toLowerCase().includes(keyword) ||
        (job.error_message || "").toLowerCase().includes(keyword);
      return matchesKeyword && (statusFilter === "all" || job.status === statusFilter) && (typeFilter === "all" || job.job_type === typeFilter);
    });
  }, [jobs, search, statusFilter, typeFilter]);

  const columns = useMemo(
    () =>
      columnHelper.columns([
        columnHelper.accessor("job_type", { id: "job_type", header: "任务", sortFn: "alphanumeric", cell: (info) => <JobName job={info.row.original} /> }),
        columnHelper.accessor("status", { id: "status", header: "状态", sortFn: "alphanumeric", cell: (info) => <JobStatus status={info.getValue()} /> }),
        columnHelper.accessor((job) => completedCount(job), { id: "handled_count", header: "处理结果", sortFn: "basic", cell: (info) => <JobCount job={info.row.original} /> }),
        columnHelper.accessor((job) => progressPercent(job), { id: "progress", header: "进度", sortFn: "basic", cell: (info) => <JobProgress job={info.row.original} /> }),
        columnHelper.accessor("created_at", { id: "created_at", header: "创建时间", sortFn: "datetime", sortDescFirst: true, cell: (info) => formatDateTime(info.getValue()) }),
        columnHelper.accessor((job) => durationSeconds(job), { id: "duration", header: "耗时", sortFn: "basic", cell: (info) => formatDuration(info.row.original) }),
        columnHelper.accessor("error_message", { id: "error_message", header: "说明 / 错误", sortFn: "alphanumeric", cell: (info) => <JobMessage value={info.getValue()} /> })
      ]),
    []
  );
  const table = useTable({
    features: jobTableFeatures,
    data: filteredJobs,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    enableSortingRemoval: true
  });

  async function refreshJobs(nextPage = meta.page, options: { silent?: boolean; pageSize?: number } = {}) {
    const nextPageSize = options.pageSize ?? pageSize;
    options.silent ? setRefreshing(true) : setLoading(true);
    if (!options.silent) setError(null);
    try {
      const result = await listJobs(nextPage, nextPageSize);
      setJobs(result.data);
      setMeta(result.meta);
      setPageSize(result.meta.page_size);
      setLastRefreshedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务日志加载失败");
    } finally {
      options.silent ? setRefreshing(false) : setLoading(false);
    }
  }

  async function handlePageSizeChange(nextPageSize: number) {
    setPageSize(nextPageSize);
    await refreshJobs(1, { pageSize: nextPageSize });
  }

  async function triggerJob(action: (typeof jobActions)[number]) {
    setRunningAction(action.label);
    setMessage(null);
    setError(null);
    try {
      const createdJob = await apiPost<JobRun>(action.path, action.body);
      setJobs((currentJobs) => [createdJob, ...currentJobs.filter((job) => job.id !== createdJob.id)]);
      setMessage(`${action.label}任务已创建`);
      await refreshJobs(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setRunningAction(null);
    }
  }

  async function triggerDailyPipeline() {
    setRunningAction("一键生成今日简报");
    setMessage(null);
    setError(null);
    try {
      const createdJobs = await triggerDailyPipelineJob();
      const createdJobIds = new Set(createdJobs.map((job) => job.id));
      setJobs((currentJobs) => [...createdJobs, ...currentJobs.filter((job) => !createdJobIds.has(job.id))]);
      setMessage(`今日简报流程已创建：${createdJobs.map((job) => jobTypeLabel(job.job_type)).join(" → ")}`);
      await refreshJobs(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setRunningAction(null);
    }
  }

  async function triggerDigest() {
    setRunningAction("发布今日简报");
    setMessage(null);
    setError(null);
    try {
      const createdJob = await apiPost<JobRun>("/api/v1/admin/jobs/generate-digest", { digest_date: formatDateParam(new Date()) });
      setJobs((currentJobs) => [createdJob, ...currentJobs.filter((job) => job.id !== createdJob.id)]);
      setMessage("发布今日简报任务已创建");
      await refreshJobs(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setRunningAction(null);
    }
  }

  useEffect(() => {
    void refreshJobs(1);
  }, []);

  useEffect(() => {
    if (activeCount === 0) return;
    const timer = window.setInterval(() => void refreshJobs(meta.page, { silent: true }), 3000);
    return () => window.clearInterval(timer);
  }, [activeCount, meta.page, pageSize]);

  return (
    <PageScaffold className="managementPage jobManagementPage">
      <PageHeader
        eyebrow="管理员 / 任务运行"
        title="任务日志"
        description="监控采集与简报任务，运行中的记录每 3 秒自动刷新。"
        actions={
          <div className="managementPageActions">
            <button className="ghostButton iconTextButton" type="button" onClick={() => void refreshJobs(meta.page)} title="刷新任务"><RefreshCw className={refreshing ? "spin" : ""} size={16} aria-hidden="true" />刷新</button>
            <button className="ghostButton iconTextButton" type="button" onClick={() => setCommandOpen(true)}><TerminalSquare size={16} aria-hidden="true" />单步任务</button>
            <button type="button" disabled={runningAction !== null} onClick={() => void triggerDailyPipeline()}><WandSparkles size={17} aria-hidden="true" />{runningAction === "一键生成今日简报" ? "创建中" : "生成今日简报"}</button>
          </div>
        }
      />

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="danger" compact>{error}</Notice> : null}

      <section className="managementMetricStrip" aria-label="任务摘要">
        <AdminMetric icon={<ListChecks size={18} />} label="任务总数" value={meta.total} detail={`当前第 ${meta.page} 页`} />
        <AdminMetric icon={<Activity size={18} />} label="执行中" value={activeCount} detail="等待或正在运行" tone={activeCount ? "warning" : "default"} />
        <AdminMetric icon={<CircleCheck size={18} />} label="本页成功" value={successCount} detail="已完成任务" tone="success" />
        <AdminMetric icon={<CircleAlert size={18} />} label="本页异常" value={abnormalCount} detail="失败或部分成功" tone={abnormalCount ? "danger" : "default"} />
      </section>

      <section className="managementWorkflow" aria-label="简报处理流程">
        <div className="managementWorkflowHeading"><span><Clock3 size={16} />简报流水线</span><small>{refreshing ? "正在刷新" : lastRefreshedAt ? `最近刷新 ${formatTime(lastRefreshedAt)}` : "等待首次刷新"}</small></div>
        <ol>{pipelineSteps.map((step, index) => <li key={step}><span>{index + 1}</span><strong>{step}</strong></li>)}</ol>
      </section>

      <section className="managementWorkspace">
        <div className="managementToolbar">
          <div className="managementToolbarTitle"><div><h2>任务记录</h2><p>查看执行状态、总量、新增、重复和失败数量。</p></div><span className="managementResultCount">{filteredJobs.length} / {jobs.length}</span></div>
          <div className="managementFilters">
            <label className="managementSearchField"><Search size={16} aria-hidden="true" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索任务、ID 或错误" /></label>
            <label className="managementFilterSelect"><select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} aria-label="筛选任务类型"><option value="all">全部类型</option>{jobTypes.map((type) => <option key={type} value={type}>{jobTypeLabel(type)}</option>)}</select><ChevronDown size={15} aria-hidden="true" /></label>
            <label className="managementFilterSelect"><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="筛选任务状态"><option value="all">全部状态</option><option value="pending">等待中</option><option value="running">运行中</option><option value="success">成功</option><option value="partial_success">部分成功</option><option value="failed">失败</option><option value="cancelled">已取消</option></select><ChevronDown size={15} aria-hidden="true" /></label>
          </div>
        </div>
        <div className="managementTableWrap jobTableWrap">
          {loading ? (
            <AdminEmptyState icon={<RefreshCw className="spin" size={20} />} title="正在加载任务" />
          ) : table.getRowModel().rows.length === 0 ? (
            <AdminEmptyState icon={<ListChecks size={22} />} title="没有匹配的任务" description="调整搜索或筛选条件。" />
          ) : (
            <table className="managementTable jobDataTable">
              <thead>{table.getHeaderGroups().map((headerGroup) => <tr key={headerGroup.id}>{headerGroup.headers.map((header) => <th key={header.id} className={`jobHeader ${header.column.id}`}>{header.isPlaceholder ? null : <button className="tableSortButton" type="button" disabled={!header.column.getCanSort()} onClick={header.column.getToggleSortingHandler()}><span><table.FlexRender header={header} /></span>{header.column.getCanSort() ? <span className="sortIndicator">{sortIndicator(header.column.getIsSorted())}</span> : null}</button>}</th>)}</tr>)}</thead>
              <tbody>{table.getRowModel().rows.map((row) => <tr key={row.id}>{row.getAllCells().map((cell) => <td key={cell.id} className={`jobCell ${cell.column.id}`}><table.FlexRender cell={cell} /></td>)}</tr>)}</tbody>
            </table>
          )}
        </div>
      </section>

      <PaginationBar meta={meta} loading={loading || refreshing} onPageChange={(nextPage) => refreshJobs(nextPage)} onPageSizeChange={handlePageSizeChange} />

      {commandOpen ? (
        <Modal title="执行单步任务" onClose={() => setCommandOpen(false)} busy={runningAction !== null} drawer>
          <div className="managementCommandPanel">
            <p className="modalIntro">单步任务用于补跑或排查处理链路。</p>
            <div className="managementCommandList">
              {jobActions.map((action) => <div className="managementCommandRow" key={action.path}><div><strong>{action.label}</strong><span>{action.description}</span></div><button className="iconAction" type="button" title={`执行${action.label}`} aria-label={`执行${action.label}`} disabled={runningAction !== null} onClick={() => void triggerJob(action)}><Play size={15} fill="currentColor" /></button></div>)}
              <div className="managementCommandRow"><div><strong>发布今日简报</strong><span>根据已处理内容生成今天的简报</span></div><button className="iconAction" type="button" title="发布今日简报" aria-label="发布今日简报" disabled={runningAction !== null} onClick={() => void triggerDigest()}><Play size={15} fill="currentColor" /></button></div>
            </div>
            {runningAction ? <div className="managementCommandStatus"><RefreshCw className="spin" size={15} />正在创建：{runningAction}</div> : null}
          </div>
        </Modal>
      ) : null}
    </PageScaffold>
  );
}

function JobName({ job }: { job: JobRun }) {
  return <div className="jobNameCell"><strong>{jobTypeLabel(job.job_type)}</strong><span>{job.trigger_type} · {job.id.slice(0, 8)}</span></div>;
}

function JobStatus({ status }: { status: string }) {
  const tone = status === "success" ? "success" : status === "failed" ? "danger" : status === "partial_success" ? "warning" : status === "running" ? "info" : "neutral";
  return <AdminStatusBadge tone={tone}>{statusLabel(status)}</AdminStatusBadge>;
}

function JobCount({ job }: { job: JobRun }) {
  const duplicateCount = job.duplicate_count ?? 0;
  const total = job.total_count > 0 ? `${job.total_count} 条` : "-";
  const totalLabel = jobTotalLabel(job.job_type);
  const successLabel = jobSuccessLabel(job.job_type);
  return <div className="jobCountCell"><strong>{totalLabel} {total}</strong><span>{successLabel} {job.success_count} · 重复 {duplicateCount} · 失败 {job.failure_count}</span></div>;
}

function JobMessage({ value }: { value: string | null }) {
  if (!value) return <span className="mutedText">-</span>;
  const summary = value.length > 56 ? `${value.slice(0, 56)}...` : value;
  return <details className="jobMessageCell"><summary>{summary}</summary><p>{value}</p></details>;
}

function JobProgress({ job }: { job: JobRun }) {
  const percent = progressPercent(job);
  const isActive = job.status === "pending" || job.status === "running";
  return <div className="jobProgressCell"><div className={`progressTrack ${isActive && job.total_count === 0 ? "indeterminate" : ""}`}><span style={{ width: `${percent}%` }} /></div><span className="mutedText">{job.status === "pending" ? "等待后台执行" : job.status === "running" && job.total_count === 0 ? "执行中" : `${percent}%`}</span></div>;
}

function progressPercent(job: JobRun) {
  const completed = completedCount(job);
  return job.total_count > 0 ? Math.min(100, Math.round((completed / job.total_count) * 100)) : 0;
}

function completedCount(job: JobRun) {
  return job.success_count + (job.duplicate_count ?? 0) + job.failure_count;
}

function jobTotalLabel(jobType: string) {
  const labels: Record<string, string> = {
    collect: "拉取",
    normalize: "整理",
    rank: "评分",
    dedupe: "候选",
    summarize: "摘要",
    generate_digest: "发布",
    publish_digest: "发布"
  };
  return labels[jobType] ?? "处理";
}

function jobSuccessLabel(jobType: string) {
  const labels: Record<string, string> = {
    collect: "新增",
    normalize: "生成",
    rank: "评分",
    dedupe: "归并",
    summarize: "摘要",
    generate_digest: "发布",
    publish_digest: "发布"
  };
  return labels[jobType] ?? "成功";
}

function statusLabel(status: string) {
  const labels: Record<string, string> = { pending: "等待中", running: "运行中", success: "成功", failed: "失败", partial_success: "部分成功", cancelled: "已取消" };
  return labels[status] ?? status;
}

function jobTypeLabel(jobType: string) {
  const labels: Record<string, string> = { collect: "抓取内容", normalize: "整理内容", rank: "计算热度", dedupe: "合并相似内容", summarize: "生成中文摘要", generate_digest: "发布今日简报", publish_digest: "发布简报" };
  return labels[jobType] ?? jobType;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function formatDateParam(value: Date) {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatTime(value: Date) {
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(value);
}

function formatDuration(job: JobRun) {
  const seconds = durationSeconds(job);
  if (job.status === "pending") return "-";
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function durationSeconds(job: JobRun) {
  const start = job.started_at ? new Date(job.started_at) : new Date(job.created_at);
  const end = job.ended_at ? new Date(job.ended_at) : new Date();
  return Math.max(0, Math.round((end.getTime() - start.getTime()) / 1000));
}

function sortIndicator(value: false | "asc" | "desc") {
  if (value === "asc") return <ArrowUp size={13} />;
  if (value === "desc") return <ArrowDown size={13} />;
  return <ArrowUpDown size={13} />;
}
