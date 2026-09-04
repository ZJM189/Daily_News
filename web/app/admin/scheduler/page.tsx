"use client";

import { FormEvent, useEffect, useState } from "react";
import { listSchedulerConfigs, updateSchedulerConfig } from "../../../lib/api";
import type { SchedulerConfig } from "../../../lib/types";

export default function AdminSchedulerPage() {
  const [configs, setConfigs] = useState<SchedulerConfig[]>([]);
  const [editing, setEditing] = useState<SchedulerConfig | null>(null);
  const [form, setForm] = useState({
    name: "",
    cron_expression: "0 8 * * *",
    timezone: "Asia/Shanghai",
    enabled: true
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const nextConfigs = await listSchedulerConfigs();
      setConfigs(nextConfigs);
      if (!editing && nextConfigs[0]) {
        startEdit(nextConfigs[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "调度配置加载失败");
    } finally {
      setLoading(false);
    }
  }

  function startEdit(config: SchedulerConfig) {
    setEditing(config);
    setForm({
      name: config.name,
      cron_expression: config.cron_expression,
      timezone: config.timezone,
      enabled: config.enabled
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) {
      return;
    }
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const saved = await updateSchedulerConfig(editing.id, {
        name: form.name,
        cron_expression: form.cron_expression,
        timezone: form.timezone,
        enabled: form.enabled,
        params: editing.params
      });
      setMessage("调度配置已更新");
      setEditing(saved);
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
    <main className="pageSurface">
      <section className="pageHeader">
        <div>
          <p className="eyebrow">管理员</p>
          <h1>调度配置</h1>
          <p className="description">配置后台自动任务的 cron、时区和启停状态。默认每日 8 点生成中文简报。</p>
        </div>
        <button className="ghostButton" type="button" onClick={() => void refresh()}>
          刷新
        </button>
      </section>

      {message ? <section className="infoState">{message}</section> : null}
      {error ? <section className="errorState compact">{error}</section> : null}

      <section className="adminSplit">
        <form className="adminForm" onSubmit={handleSubmit}>
          <h2>编辑调度</h2>
          {editing ? (
            <>
              <label>
                <span>名称</span>
                <input
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  required
                />
              </label>
              <label>
                <span>Cron 表达式</span>
                <input
                  value={form.cron_expression}
                  onChange={(event) => setForm({ ...form, cron_expression: event.target.value })}
                  placeholder="0 8 * * *"
                  required
                />
              </label>
              <label>
                <span>时区</span>
                <input
                  value={form.timezone}
                  onChange={(event) => setForm({ ...form, timezone: event.target.value })}
                  placeholder="Asia/Shanghai"
                  required
                />
              </label>
              <label className="inlineCheck">
                <input
                  type="checkbox"
                  checked={form.enabled}
                  onChange={(event) => setForm({ ...form, enabled: event.target.checked })}
                />
                启用该调度
              </label>
              <button type="submit" disabled={saving}>
                {saving ? "保存中" : "保存配置"}
              </button>
              <p className="mutedText">示例：每天 8 点是 `0 8 * * *`，每小时是 `0 * * * *`。</p>
            </>
          ) : (
            <div className="emptyState">暂无可编辑调度。</div>
          )}
        </form>

        <section className="tableWrap">
          {loading ? (
            <div className="emptyState">正在加载调度配置</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>任务</th>
                  <th>Cron</th>
                  <th>时区</th>
                  <th>状态</th>
                  <th>更新时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {configs.map((config) => (
                  <tr key={config.id}>
                    <td>
                      <strong>{config.name}</strong>
                      <br />
                      <span className="mutedText">{config.job_type}</span>
                    </td>
                    <td>{config.cron_expression}</td>
                    <td>{config.timezone}</td>
                    <td>
                      <span className={`statusBadge ${config.enabled ? "success" : "failed"}`}>
                        {config.enabled ? "启用" : "停用"}
                      </span>
                    </td>
                    <td>{formatDateTime(config.updated_at)}</td>
                    <td>
                      <button className="ghostButton" type="button" onClick={() => startEdit(config)}>
                        编辑
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </section>
    </main>
  );
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}
