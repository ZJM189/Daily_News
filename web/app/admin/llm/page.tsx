"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  CardHeader,
  Notice,
  PageHeader,
  PageScaffold
} from "../../components/UiPrimitives";
import {
  createLLMProvider,
  listLLMProviders,
  setDefaultLLMProvider,
  updateLLMProvider
} from "../../../lib/api";
import type { LLMProvider } from "../../../lib/types";

export default function AdminLlmPage() {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    base_url: "",
    model: "",
    api_key: "",
    timeout_seconds: 60,
    retry_count: 2,
    enabled: true,
    is_default: false
  });

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const nextProviders = await listLLMProviders();
      setProviders(nextProviders);
      if (editingProvider) {
        const nextEditing = nextProviders.find((provider) => provider.id === editingProvider.id) ?? null;
        setEditingProvider(nextEditing);
        if (nextEditing) {
          setForm({
            name: nextEditing.name,
            base_url: nextEditing.base_url,
            model: nextEditing.model,
            api_key: "",
            timeout_seconds: nextEditing.timeout_seconds,
            retry_count: nextEditing.retry_count,
            enabled: nextEditing.enabled,
            is_default: nextEditing.is_default
          });
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Provider 加载失败");
    } finally {
      setLoading(false);
    }
  }

  function startEdit(provider: LLMProvider) {
    setEditingProvider(provider);
    setForm({
      name: provider.name,
      base_url: provider.base_url,
      model: provider.model,
      api_key: "",
      timeout_seconds: provider.timeout_seconds,
      retry_count: provider.retry_count,
      enabled: provider.enabled,
      is_default: provider.is_default
    });
  }

  function resetEditor() {
    setEditingProvider(null);
    setForm({
      name: "",
      base_url: "",
      model: "",
      api_key: "",
      timeout_seconds: 60,
      retry_count: 2,
      enabled: true,
      is_default: false
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      if (editingProvider) {
        await updateLLMProvider(editingProvider.id, {
          name: form.name,
          base_url: form.base_url,
          model: form.model,
          api_key: form.api_key ? form.api_key : undefined,
          timeout_seconds: form.timeout_seconds,
          retry_count: form.retry_count,
          enabled: form.enabled,
          is_default: form.is_default
        });
        setMessage("LLM Provider 已更新");
      } else {
        await createLLMProvider({
          ...form,
          api_key: form.api_key || null
        });
        setMessage("LLM Provider 已创建");
      }
      resetEditor();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存 Provider 失败");
    } finally {
      setSaving(false);
    }
  }

  async function makeDefault(provider: LLMProvider) {
    setMessage(null);
    setError(null);
    try {
      await setDefaultLLMProvider(provider.id);
      setMessage("默认 Provider 已更新");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "设置默认失败");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <PageScaffold>
      <PageHeader
        eyebrow="管理员"
        title="LLM 设置"
        description="配置 OpenAI-compatible Provider、默认模型、密钥脱敏和调用超时重试。"
        actions={
        <button className="ghostButton" type="button" onClick={() => void refresh()}>
          刷新
        </button>
        }
      />

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="danger" compact>{error}</Notice> : null}

      <section className="adminSplit">
        <form className="adminForm" onSubmit={handleSubmit}>
          <CardHeader
            title={editingProvider ? "编辑 Provider" : "新增 Provider"}
            description={editingProvider ? `正在编辑：${editingProvider.name}` : "新增一个 OpenAI-compatible 模型服务。"}
          />
          <label>
            <span>名称</span>
            <input
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="例如：OpenAI"
              required
            />
          </label>
          <label>
            <span>Base URL</span>
            <input
              value={form.base_url}
              onChange={(event) => setForm({ ...form, base_url: event.target.value })}
              placeholder="https://api.openai.com/v1"
              required
            />
          </label>
          <label>
            <span>模型</span>
            <input
              value={form.model}
              onChange={(event) => setForm({ ...form, model: event.target.value })}
              placeholder="例如：gpt-4o-mini"
              required
            />
          </label>
          <label>
            <span>API Key</span>
            <input
              type="password"
              value={form.api_key}
              onChange={(event) => setForm({ ...form, api_key: event.target.value })}
              placeholder={editingProvider ? "留空表示不修改" : "可选，保存后脱敏"}
            />
          </label>
          <div className="formGridTwo">
            <label>
              <span>超时秒数</span>
              <input
                type="number"
                min="1"
                max="600"
                value={form.timeout_seconds}
                onChange={(event) =>
                  setForm({ ...form, timeout_seconds: Number(event.target.value) })
                }
              />
            </label>
            <label>
              <span>重试次数</span>
              <input
                type="number"
                min="0"
                max="10"
                value={form.retry_count}
                onChange={(event) => setForm({ ...form, retry_count: Number(event.target.value) })}
              />
            </label>
          </div>
          <label className="inlineCheck">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => setForm({ ...form, enabled: event.target.checked })}
            />
            启用
          </label>
          <label className="inlineCheck">
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={(event) => setForm({ ...form, is_default: event.target.checked })}
            />
            设为默认
          </label>
          <button type="submit" disabled={saving}>
            {saving ? "保存中" : editingProvider ? "更新 Provider" : "保存 Provider"}
          </button>
          {editingProvider ? (
            <button className="ghostButton" type="button" onClick={resetEditor}>
              取消编辑
            </button>
          ) : null}
        </form>

        <section className="tableWrap tableCard">
          <div className="tableCardHeader">
            <h2>Provider 列表</h2>
            <p className="mutedText">管理默认模型、启停状态、调用超时和重试策略。</p>
          </div>
          {loading ? (
            <div className="emptyState">正在加载 Provider</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>名称</th>
                  <th>模型</th>
                  <th>状态</th>
                  <th>密钥</th>
                  <th>调用配置</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((provider) => (
                  <tr key={provider.id}>
                    <td>
                      <strong>{provider.name}</strong>
                      <br />
                      <span className="mutedText">{provider.base_url}</span>
                    </td>
                    <td>{provider.model}</td>
                    <td>
                      <div className="digestMeta">
                        <span className={`statusBadge ${provider.enabled ? "success" : "failed"}`}>
                          {provider.enabled ? "启用" : "禁用"}
                        </span>
                        {provider.is_default ? <span className="statusBadge success">默认</span> : null}
                      </div>
                    </td>
                    <td>{provider.api_key_masked || "未配置"}</td>
                    <td>
                      {provider.timeout_seconds}s / 重试 {provider.retry_count}
                    </td>
                    <td>
                      <button
                        className="ghostButton"
                        type="button"
                        disabled={provider.is_default}
                        onClick={() => void makeDefault(provider)}
                      >
                        设为默认
                      </button>
                      <button className="ghostButton" type="button" onClick={() => startEdit(provider)}>
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
    </PageScaffold>
  );
}
