"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CalendarClock,
  ChevronDown,
  Clock3,
  Globe2,
  Pencil,
  RefreshCw,
  Search,
  TimerOff
} from "lucide-react";
import {
  AdminEmptyState,
  AdminMetric,
  AdminStatusBadge
} from "../../components/AdminPrimitives";
import { Modal } from "../../components/Modal";
import { Notice, PageHeader, PageScaffold } from "../../components/UiPrimitives";
import { listSchedulerConfigs, updateSchedulerConfig } from "../../../lib/api";
import type { SchedulerConfig } from "../../../lib/types";

export default function AdminSchedulerPage() {
  const [configs, setConfigs] = useState<SchedulerConfig[]>([]);
  const [editing, setEditing] = useState<SchedulerConfig | null>(null);
  const [form, setForm] = useState({ name: "", cron_expression: "0 8 * * *", timezone: "Asia/Shanghai", enabled: true });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filteredConfigs = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return configs.filter((config) => {
      const matchesKeyword =
        !keyword ||
        config.name.toLowerCase().includes(keyword) ||
        config.job_type.toLowerCase().includes(keyword) ||
        config.timezone.toLowerCase().includes(keyword);
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "enabled" && config.enabled) ||
        (statusFilter === "disabled" && !config.enabled);
      return matchesKeyword && matchesStatus;
    });
  }, [configs, search, statusFilter]);

  const enabledCount = configs.filter((config) => config.enabled).length;
  const timezoneCount = new Set(configs.map((config) => config.timezone)).size;
  const recentlyUpdatedCount = configs.filter((config) => Date.now() - new Date(config.updated_at).getTime() < 7 * 24 * 60 * 60 * 1000).length;

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const nextConfigs = await listSchedulerConfigs();
      setConfigs(nextConfigs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "调度配置加载失败");
    } finally {
      setLoading(false);
    }
  }

  function startEdit(config: SchedulerConfig) {
    setEditing(config);
    setForm(formFromConfig(config));
  }

  function closeEditor() {
    setEditing(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await updateSchedulerConfig(editing.id, {
        name: form.name,
        cron_expression: form.cron_expression,
        timezone: form.timezone,
        enabled: form.enabled,
        params: editing.params
      });
      setMessage("调度配置已更新");
      closeEditor();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存调度配置失败");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <PageScaffold className="managementPage">
      <PageHeader
        eyebrow="管理员 / 自动化"
        title="调度配置"
        description="管理后台自动任务的执行时间、时区和启停状态。"
        actions={<div className="managementPageActions"><button className="ghostButton" type="button" onClick={() => void refresh()} title="刷新列表"><RefreshCw size={16} aria-hidden="true" />刷新</button></div>}
      />

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="danger" compact>{error}</Notice> : null}

      <section className="managementMetricStrip" aria-label="调度摘要">
        <AdminMetric icon={<CalendarClock size={18} />} label="调度任务" value={configs.length} detail="已配置自动任务" />
        <AdminMetric icon={<Clock3 size={18} />} label="启用中" value={enabledCount} detail="将按计划自动执行" tone="success" />
        <AdminMetric icon={<TimerOff size={18} />} label="已停用" value={configs.length - enabledCount} detail="不会自动触发" tone={configs.length - enabledCount ? "warning" : "default"} />
        <AdminMetric icon={<Globe2 size={18} />} label="时区" value={timezoneCount} detail={`${recentlyUpdatedCount} 个近 7 天更新`} />
      </section>

      <section className="managementWorkspace">
        <div className="managementToolbar">
          <div className="managementToolbarTitle"><div><h2>调度任务</h2><p>查看任务类型、Cron、时区和最近更新时间。</p></div><span className="managementResultCount">{filteredConfigs.length} / {configs.length}</span></div>
          <div className="managementFilters">
            <label className="managementSearchField"><Search size={16} aria-hidden="true" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索任务名称、类型或时区" /></label>
            <label className="managementFilterSelect"><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="筛选调度状态"><option value="all">全部状态</option><option value="enabled">启用</option><option value="disabled">停用</option></select><ChevronDown size={15} aria-hidden="true" /></label>
          </div>
        </div>

        {loading ? (
          <AdminEmptyState icon={<RefreshCw className="spin" size={20} />} title="正在加载调度配置" />
        ) : filteredConfigs.length ? (
          <div className="managementTableWrap">
            <table className="managementTable schedulerManagementTable">
              <thead><tr><th>任务</th><th>Cron</th><th>时区</th><th>状态</th><th>更新时间</th><th>操作</th></tr></thead>
              <tbody>
                {filteredConfigs.map((config) => (
                  <tr key={config.id}>
                    <td><div className="managementNameCell"><span className="managementIdentityMark"><CalendarClock size={16} /></span><div><strong>{config.name}</strong><small>{jobTypeLabel(config.job_type)}</small></div></div></td>
                    <td><code className="managementCode">{config.cron_expression}</code></td>
                    <td><span className="managementSecondaryText">{config.timezone}</span></td>
                    <td><AdminStatusBadge tone={config.enabled ? "success" : "neutral"}>{config.enabled ? "启用" : "停用"}</AdminStatusBadge></td>
                    <td><span className="managementSecondaryText">{formatDateTime(config.updated_at)}</span></td>
                    <td><div className="managementRowActions"><button className="iconAction" type="button" title="编辑调度" aria-label={`编辑 ${config.name}`} onClick={() => startEdit(config)}><Pencil size={15} /></button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <AdminEmptyState icon={<CalendarClock size={22} />} title="没有匹配的调度任务" description="调整搜索或状态筛选。" />
        )}
      </section>

      {editing ? (
        <Modal title="编辑调度" onClose={closeEditor} busy={saving} drawer>
          <form className="managementEditorForm" onSubmit={handleSubmit}>
            <p className="modalIntro">更新「{editing.name}」的自动执行计划。</p>
            <label><span>名称</span><input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
            <label><span>Cron 表达式</span><input value={form.cron_expression} onChange={(event) => setForm({ ...form, cron_expression: event.target.value })} placeholder="0 8 * * *" required /><small>每天 8 点：0 8 * * *；每小时：0 * * * *</small></label>
            <label><span>时区</span><input value={form.timezone} onChange={(event) => setForm({ ...form, timezone: event.target.value })} placeholder="Asia/Shanghai" required /></label>
            <div className="managementToggleGroup"><label className="inlineCheck"><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} />启用该调度</label></div>
            <div className="modalActions"><button className="ghostButton" type="button" onClick={closeEditor}>取消</button><button type="submit" disabled={saving}>{saving ? "保存中" : "保存配置"}</button></div>
          </form>
        </Modal>
      ) : null}
    </PageScaffold>
  );
}

function formFromConfig(config: SchedulerConfig) {
  return { name: config.name, cron_expression: config.cron_expression, timezone: config.timezone, enabled: config.enabled };
}

function jobTypeLabel(value: string) {
  const labels: Record<string, string> = { daily_pipeline: "每日处理链路", collect: "抓取内容", normalize: "整理内容", rank: "计算热度", dedupe: "合并相似内容", summarize: "生成中文摘要", generate_digest: "发布今日简报" };
  return labels[value] ?? value;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}
