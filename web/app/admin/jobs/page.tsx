"use client";

import { useEffect, useState } from "react";
import { apiPost, listJobs, triggerDailyPipelineJob } from "../../../lib/api";
import type { JobRun } from "../../../lib/types";

const jobActions = [
  { label: "采集", path: "/api/v1/admin/jobs/collect", body: { source_types: [] } },
  { label: "标准化", path: "/api/v1/admin/jobs/normalize", body: { limit: 5000 } },
  { label: "评分", path: "/api/v1/admin/jobs/rank", body: { limit: 500 } },
  { label: "专题聚合", path: "/api/v1/admin/jobs/dedupe", body: { limit: 1000 } },
  { label: "中文摘要", path: "/api/v1/admin/jobs/summarize", body: { limit: 20, min_score: 70 } }
];

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<JobRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

  const activeCount = jobs.filter((job) => job.status === "pending" || job.status === "running").length;

  async function refreshJobs(options: { silent?: boolean } = {}) {
    if (options.silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    try {
      setJobs(await listJobs());
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
      setMessage(`${action.label}任务已创建，worker 会自动执行`);
      await refreshJobs();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setRunningAction(null);
    }
  }

  async function triggerDailyPipeline() {
    setRunningAction("完整链路");
    setMessage(null);
    try {
      const createdJobs = await triggerDailyPipelineJob();
      const createdJobIds = new Set(createdJobs.map((job) => job.id));
      setJobs((currentJobs) => [
        ...createdJobs,
        ...currentJobs.filter((job) => !createdJobIds.has(job.id))
      ]);
      setMessage(`完整链路任务已创建：${createdJobs.map((job) => job.job_type).join(" → ")}`);
      await refreshJobs();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setRunningAction(null);
    }
  }

  async function triggerDigest() {
    const today = formatDateParam(new Date());
    setRunningAction("生成简报");
    setMessage(null);
    try {
      const createdJob = await apiPost<JobRun>("/api/v1/admin/jobs/generate-digest", { digest_date: today });
      setJobs((currentJobs) => [createdJob, ...currentJobs.filter((job) => job.id !== createdJob.id)]);
      setMessage("生成简报任务已创建，worker 会自动执行");
      await refreshJobs();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setRunningAction(null);
    }
  }

  useEffect(() => {
    void refreshJobs();
  }, []);

  useEffect(() => {
    if (activeCount === 0) {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshJobs({ silent: true });
    }, 3000);

    return () => window.clearInterval(timer);
  }, [activeCount]);

  return (
    <main className="pageSurface">
      <section className="toolbar">
        <div>
          <p className="eyebrow">管理员</p>
          <h1>任务日志</h1>
          <p className="description">查看后台任务状态，并手动触发数据处理链路。存在等待或运行任务时会每 3 秒自动刷新。</p>
        </div>
        <div className="toolbarActions">
          <span className="mutedText">
            {refreshing ? "刷新中" : lastRefreshedAt ? `最近刷新 ${formatTime(lastRefreshedAt)}` : ""}
          </span>
          <button type="button" disabled={runningAction !== null} onClick={() => void triggerDailyPipeline()}>
            {runningAction === "完整链路" ? "创建中" : "一键执行完整链路"}
          </button>
          <button className="ghostButton" type="button" onClick={() => void refreshJobs()}>
            刷新
          </button>
        </div>
      </section>

      <section className="actionBar">
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
          {runningAction === "生成简报" ? "创建中" : "生成简报"}
        </button>
      </section>

      {message ? <section className="infoState">{message}</section> : null}

      <section className="jobSummaryGrid">
        <div className="metricTile">
          <span>等待执行</span>
          <strong>{jobs.filter((job) => job.status === "pending").length}</strong>
        </div>
        <div className="metricTile">
          <span>正在运行</span>
          <strong>{jobs.filter((job) => job.status === "running").length}</strong>
        </div>
        <div className="metricTile">
          <span>最近成功</span>
          <strong>{jobs.filter((job) => job.status === "success").length}</strong>
        </div>
        <div className="metricTile">
          <span>最近失败</span>
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
                <th>类型</th>
                <th>状态</th>
                <th>统计</th>
                <th>进度</th>
                <th>创建时间</th>
                <th>耗时</th>
                <th>错误</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.job_type}</td>
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
          ? "等待 worker 拾取"
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
