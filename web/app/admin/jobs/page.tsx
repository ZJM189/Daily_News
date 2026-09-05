"use client";

import { useEffect, useState } from "react";
import { PaginationBar } from "../../components/PaginationBar";
import { apiPost, listJobs, triggerDailyPipelineJob } from "../../../lib/api";
import type { JobRun, PageMeta } from "../../../lib/types";

const jobActions = [
  { label: "抓取内容", path: "/api/v1/admin/jobs/collect", body: { source_types: [] } },
  { label: "整理内容", path: "/api/v1/admin/jobs/normalize", body: { limit: 5000 } },
  { label: "计算热度", path: "/api/v1/admin/jobs/rank", body: { limit: 500 } },
  { label: "合并相似内容", path: "/api/v1/admin/jobs/dedupe", body: { limit: 1000 } },
  { label: "生成中文摘要", path: "/api/v1/admin/jobs/summarize", body: { limit: 20, min_score: 70 } }
];

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<JobRun[]>([]);
  const [meta, setMeta] = useState<PageMeta>({ page: 1, page_size: 20, total: 0 });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

  const activeCount = jobs.filter((job) => job.status === "pending" || job.status === "running").length;

  async function refreshJobs(nextPage = meta.page, options: { silent?: boolean } = {}) {
    if (options.silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    try {
      const result = await listJobs(nextPage);
      setJobs(result.data);
      setMeta(result.meta);
      setLastRefreshedAt(new Date());
    } finally {
      if (options.silent) {
        setRefreshing(false);
      } else {
        setLoading(false);
      }
    }
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
  }, [activeCount, meta.page]);

  return (
    <main className="pageSurface">
      <section className="toolbar">
        <div>
          <p className="eyebrow">管理员</p>
          <h1>任务日志</h1>
          <p className="description">查看采集和简报生成进度。存在等待或运行任务时，页面会每 3 秒自动刷新。</p>
        </div>
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
      </section>

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

      <section className="manualJobPanel">
        <div>
          <h2>单步重跑（高级）</h2>
          <p className="mutedText">通常直接使用“一键生成今日简报”。下面按钮用于排查或补跑某个环节。</p>
        </div>
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
      </section>

      {message ? <section className="infoState">{message}</section> : null}

      <section className="jobSummaryGrid">
        <div className="metricTile">
          <span>任务总数</span>
          <strong>{meta.total}</strong>
        </div>
        <div className="metricTile">
          <span>本页等待</span>
          <strong>{jobs.filter((job) => job.status === "pending").length}</strong>
        </div>
        <div className="metricTile">
          <span>本页运行</span>
          <strong>{jobs.filter((job) => job.status === "running").length}</strong>
        </div>
        <div className="metricTile">
          <span>本页异常</span>
          <strong>{jobs.filter((job) => job.status === "failed" || job.status === "partial_success").length}</strong>
        </div>
      </section>

      <section className="tableWrap">
        {loading ? (
          <div className="emptyState">正在加载任务</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>任务</th>
                <th>状态</th>
                <th>处理数量</th>
                <th>进度</th>
                <th>创建时间</th>
                <th>耗时</th>
                <th>说明/错误</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{jobTypeLabel(job.job_type)}</td>
                  <td>
                    <span className={`statusBadge ${job.status}`}>{statusLabel(job.status)}</span>
                  </td>
                  <td>
                    {job.success_count}/{job.total_count || "-"}
                    {job.failure_count ? `, 失败 ${job.failure_count}` : ""}
                  </td>
                  <td>
                    <JobProgress job={job} />
                  </td>
                  <td>{formatDateTime(job.created_at)}</td>
                  <td>{formatDuration(job)}</td>
                  <td>{job.error_message || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <PaginationBar meta={meta} loading={loading || refreshing} onPageChange={refreshJobs} />
    </main>
  );
}

function JobProgress({ job }: { job: JobRun }) {
  const completedCount = job.success_count + job.failure_count;
  const percent = job.total_count > 0 ? Math.min(100, Math.round((completedCount / job.total_count) * 100)) : 0;
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
  const start = job.started_at ? new Date(job.started_at) : new Date(job.created_at);
  const end = job.ended_at ? new Date(job.ended_at) : new Date();
  const seconds = Math.max(0, Math.round((end.getTime() - start.getTime()) / 1000));
  if (job.status === "pending") {
    return "-";
  }
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}
