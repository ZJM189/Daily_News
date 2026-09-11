"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  Cpu,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Star
} from "lucide-react";
import {
  AdminEmptyState,
  AdminMetric,
  AdminStatusBadge
} from "../../components/AdminPrimitives";
import { Modal } from "../../components/Modal";
import { Notice, PageHeader, PageScaffold } from "../../components/UiPrimitives";
import {
  createLLMProvider,
  listLLMProviders,
  setDefaultLLMProvider,
  updateLLMProvider
} from "../../../lib/api";
import type { LLMProvider } from "../../../lib/types";

const emptyForm = {
  name: "",
  base_url: "",
  model: "",
  api_key: "",
  timeout_seconds: 60,
  retry_count: 2,
  enabled: true,
  is_default: false
};

export default function AdminLlmPage() {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [form, setForm] = useState(emptyForm);

  const filteredProviders = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return providers.filter((provider) => {
      const matchesKeyword =
        !keyword ||
        provider.name.toLowerCase().includes(keyword) ||
        provider.model.toLowerCase().includes(keyword) ||
        provider.base_url.toLowerCase().includes(keyword);
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "enabled" && provider.enabled) ||
        (statusFilter === "disabled" && !provider.enabled) ||
        (statusFilter === "default" && provider.is_default);
      return matchesKeyword && matchesStatus;
    });
  }, [providers, search, statusFilter]);

  const defaultProvider = providers.find((provider) => provider.is_default);
  const enabledCount = providers.filter((provider) => provider.enabled).length;
  const configuredKeyCount = providers.filter((provider) => provider.api_key_masked).length;

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const nextProviders = await listLLMProviders();
      setProviders(nextProviders);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Provider 加载失败");
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setEditingProvider(null);
    setForm(emptyForm);
    setEditorOpen(true);
  }

  function startEdit(provider: LLMProvider) {
    setEditingProvider(provider);
    setForm(formFromProvider(provider));
    setEditorOpen(true);
  }

  function closeEditor() {
    setEditorOpen(false);
    setEditingProvider(null);
    setForm(emptyForm);
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
          api_key: form.api_key || undefined,
          timeout_seconds: form.timeout_seconds,
          retry_count: form.retry_count,
          enabled: form.enabled,
          is_default: form.is_default
        });
        setMessage("LLM Provider 已更新");
      } else {
        await createLLMProvider({ ...form, api_key: form.api_key || null });
        setMessage("LLM Provider 已创建");
      }
      closeEditor();
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
      setMessage(`已将 ${provider.name} 设为默认 Provider`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "设置默认失败");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <PageScaffold className="managementPage">
      <PageHeader
        eyebrow="管理员 / 模型服务"
        title="LLM 设置"
        description="管理用于摘要、检索和内容处理的模型服务。"
        actions={
          <div className="managementPageActions">
            <button className="ghostButton" type="button" onClick={() => void refresh()} title="刷新列表">
              <RefreshCw size={16} aria-hidden="true" />
              刷新
            </button>
            <button type="button" onClick={openCreate}>
              <Plus size={17} aria-hidden="true" />
              新增 Provider
            </button>
          </div>
        }
      />

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="danger" compact>{error}</Notice> : null}

      <section className="managementMetricStrip" aria-label="Provider 摘要">
        <AdminMetric icon={<Server size={18} />} label="Provider" value={providers.length} detail="已配置模型服务" />
        <AdminMetric icon={<ShieldCheck size={18} />} label="启用中" value={enabledCount} detail="可参与模型调用" tone="success" />
        <AdminMetric icon={<Star size={18} />} label="默认模型" value={defaultProvider?.model || "未设置"} detail={defaultProvider?.name || "需要指定默认 Provider"} />
        <AdminMetric icon={<KeyRound size={18} />} label="已配置密钥" value={configuredKeyCount} detail={`${providers.length - configuredKeyCount} 个未配置`} />
      </section>

      <section className="managementWorkspace">
        <div className="managementToolbar">
          <div className="managementToolbarTitle">
            <div>
              <h2>Provider 列表</h2>
              <p>查看模型、端点、密钥状态和调用策略。</p>
            </div>
            <span className="managementResultCount">{filteredProviders.length} / {providers.length}</span>
          </div>
          <div className="managementFilters">
            <label className="managementSearchField">
              <Search size={16} aria-hidden="true" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索名称、模型或地址" />
            </label>
            <label className="managementFilterSelect">
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="筛选 Provider 状态">
                <option value="all">全部状态</option>
                <option value="enabled">启用</option>
                <option value="disabled">停用</option>
                <option value="default">默认</option>
              </select>
              <ChevronDown size={15} aria-hidden="true" />
            </label>
          </div>
        </div>

        {loading ? (
          <AdminEmptyState icon={<RefreshCw className="spin" size={20} />} title="正在加载 Provider" />
        ) : filteredProviders.length ? (
          <div className="managementTableWrap">
            <table className="managementTable">
              <thead><tr><th>Provider</th><th>模型</th><th>状态</th><th>密钥</th><th>调用策略</th><th>操作</th></tr></thead>
              <tbody>
                {filteredProviders.map((provider) => (
                  <tr key={provider.id}>
                    <td><div className="managementNameCell"><span className="managementIdentityMark"><Server size={16} /></span><div><strong>{provider.name}</strong><small title={provider.base_url}>{provider.base_url}</small></div></div></td>
                    <td><strong className="managementPrimaryText">{provider.model}</strong></td>
                    <td><div className="managementStatusGroup"><AdminStatusBadge tone={provider.enabled ? "success" : "neutral"}>{provider.enabled ? "启用" : "停用"}</AdminStatusBadge>{provider.is_default ? <AdminStatusBadge tone="info">默认</AdminStatusBadge> : null}</div></td>
                    <td><span className="managementSecondaryText">{provider.api_key_masked || "未配置"}</span></td>
                    <td><span className="managementSecondaryText">{provider.timeout_seconds}s · 重试 {provider.retry_count}</span></td>
                    <td><div className="managementRowActions"><button className="iconAction" type="button" title={provider.is_default ? "当前默认 Provider" : "设为默认"} aria-label={`将 ${provider.name} 设为默认`} disabled={provider.is_default} onClick={() => void makeDefault(provider)}><Star size={15} fill={provider.is_default ? "currentColor" : "none"} /></button><button className="iconAction" type="button" title="编辑 Provider" aria-label={`编辑 ${provider.name}`} onClick={() => startEdit(provider)}><Pencil size={15} /></button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <AdminEmptyState icon={<Cpu size={22} />} title="没有匹配的 Provider" description="调整筛选条件，或新增一个模型服务。" />
        )}
      </section>

      {editorOpen ? (
        <Modal title={editingProvider ? "编辑 Provider" : "新增 Provider"} onClose={closeEditor} busy={saving} drawer>
          <form className="managementEditorForm" onSubmit={handleSubmit}>
            <p className="modalIntro">{editingProvider ? `更新「${editingProvider.name}」的模型服务配置。` : "配置一个 OpenAI-compatible 模型服务。"}</p>
            <label><span>名称</span><input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="例如：OpenAI" required /></label>
            <label><span>Base URL</span><input value={form.base_url} onChange={(event) => setForm({ ...form, base_url: event.target.value })} placeholder="https://api.openai.com/v1" required /></label>
            <label><span>模型</span><input value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} placeholder="例如：gpt-4o-mini" required /></label>
            <label><span>API Key <small>{editingProvider ? "留空不修改" : "可选"}</small></span><input type="password" value={form.api_key} onChange={(event) => setForm({ ...form, api_key: event.target.value })} placeholder={editingProvider ? "留空表示不修改" : "保存后仅显示脱敏值"} /></label>
            <div className="formGridTwo"><label><span>超时秒数</span><input type="number" min="1" max="600" value={form.timeout_seconds} onChange={(event) => setForm({ ...form, timeout_seconds: Number(event.target.value) })} /></label><label><span>重试次数</span><input type="number" min="0" max="10" value={form.retry_count} onChange={(event) => setForm({ ...form, retry_count: Number(event.target.value) })} /></label></div>
            <div className="managementToggleGroup"><label className="inlineCheck"><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} />启用 Provider</label><label className="inlineCheck"><input type="checkbox" checked={form.is_default} onChange={(event) => setForm({ ...form, is_default: event.target.checked })} />设为默认</label></div>
            <div className="modalActions"><button className="ghostButton" type="button" onClick={closeEditor}>取消</button><button type="submit" disabled={saving}>{saving ? "保存中" : editingProvider ? "保存修改" : "创建 Provider"}</button></div>
          </form>
        </Modal>
      ) : null}
    </PageScaffold>
  );
}

function formFromProvider(provider: LLMProvider) {
  return { name: provider.name, base_url: provider.base_url, model: provider.model, api_key: "", timeout_seconds: provider.timeout_seconds, retry_count: provider.retry_count, enabled: provider.enabled, is_default: provider.is_default };
}
