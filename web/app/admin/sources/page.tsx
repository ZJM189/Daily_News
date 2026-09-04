"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  createSource,
  createSourceCredential,
  listSourceCredentials,
  listSources,
  triggerCollectJob,
  updateSource,
  updateSourceCredential
} from "../../../lib/api";
import type { Source, SourceCredential } from "../../../lib/types";

const sourceTypes = [
  { value: "rss", label: "RSS" },
  { value: "github", label: "GitHub" },
  { value: "arxiv", label: "arXiv" },
  { value: "hacker_news", label: "Hacker News" },
  { value: "product_hunt", label: "Product Hunt" },
  { value: "hugging_face", label: "Hugging Face" }
];

export default function AdminSourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [credentials, setCredentials] = useState<SourceCredential[]>([]);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingCredential, setSavingCredential] = useState(false);
  const [collectingSourceId, setCollectingSourceId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    type: "rss",
    status: "disabled",
    url: "",
    query: "",
    limit: 30,
    weight: 50,
    language: "zh",
    credential_id: "",
    credential_env_key: ""
  });
  const [credentialForm, setCredentialForm] = useState({
    name: "",
    source_type: "rss",
    secret: "",
    status: "active"
  });

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [nextSources, nextCredentials] = await Promise.all([
        listSources(),
        listSourceCredentials()
      ]);
      setSources(nextSources);
      setCredentials(nextCredentials);
      if (editingSource) {
        const nextEditing = nextSources.find((source) => source.id === editingSource.id) ?? null;
        setEditingSource(nextEditing);
        if (nextEditing) {
          setFormFromSource(nextEditing);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "来源加载失败");
    } finally {
      setLoading(false);
    }
  }

  function setFormFromSource(source: Source) {
    const queryConfig = source.query_config ?? {};
    setForm({
      name: source.name,
      type: source.type,
      status: source.status,
      url: source.url || "",
      query:
        typeof queryConfig.search_query === "string"
          ? queryConfig.search_query
          : typeof queryConfig.query === "string"
            ? queryConfig.query
            : "",
      limit:
        typeof queryConfig.limit === "number"
          ? queryConfig.limit
          : Number.isFinite(Number(queryConfig.limit))
            ? Number(queryConfig.limit)
            : 30,
      weight: source.weight,
      language: source.language || "zh",
      credential_id: source.credential_id || "",
      credential_env_key: source.credential_env_key || ""
    });
  }

  function startEdit(source: Source) {
    setEditingSource(source);
    setFormFromSource(source);
  }

  function resetEditor() {
    setEditingSource(null);
    setForm({
      name: "",
      type: "rss",
      status: "disabled",
      url: "",
      query: "",
      limit: 30,
      weight: 50,
      language: "zh",
      credential_id: "",
      credential_env_key: ""
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const queryConfig: Record<string, unknown> = {};
      if (form.query) {
        if (form.type === "arxiv") {
          queryConfig.search_query = form.query;
        } else {
          queryConfig.query = form.query;
        }
      }
      if (form.limit) {
        queryConfig.limit = form.limit;
      }
      if (editingSource) {
        await updateSource(editingSource.id, {
          name: form.name,
          status: form.status,
          url: form.url || null,
          query_config: queryConfig,
          credential_id: form.credential_id || null,
          credential_env_key: form.credential_env_key || null,
          weight: form.weight,
          language: form.language || null
        });
        setMessage("来源已更新");
      } else {
        await createSource({
          name: form.name,
          type: form.type,
          status: form.status,
          url: form.url || null,
          query_config: queryConfig,
          credential_id: form.credential_id || null,
          credential_env_key: form.credential_env_key || null,
          weight: form.weight,
          language: form.language || null
        });
        setMessage("来源已创建");
      }
      resetEditor();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存来源失败");
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus(source: Source) {
    setMessage(null);
    setError(null);
    try {
      const nextStatus = source.status === "enabled" ? "disabled" : "enabled";
      await updateSource(source.id, { status: nextStatus });
      setMessage(nextStatus === "enabled" ? "来源已启用" : "来源已停用");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新来源失败");
    }
  }

  async function collectSource(source: Source) {
    setCollectingSourceId(source.id);
    setMessage(null);
    setError(null);
    try {
      await triggerCollectJob({ source_id: source.id });
      setMessage(`${source.name} 采集任务已创建`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建采集任务失败");
    } finally {
      setCollectingSourceId(null);
    }
  }

  async function handleCreateCredential(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingCredential(true);
    setMessage(null);
    setError(null);
    try {
      await createSourceCredential(credentialForm);
      setMessage("来源凭据已创建");
      setCredentialForm({ ...credentialForm, name: "", secret: "" });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建凭据失败");
    } finally {
      setSavingCredential(false);
    }
  }

  async function toggleCredentialStatus(credential: SourceCredential) {
    setMessage(null);
    setError(null);
    try {
      const nextStatus = credential.status === "active" ? "disabled" : "active";
      await updateSourceCredential(credential.id, { status: nextStatus });
      setMessage(nextStatus === "active" ? "凭据已启用" : "凭据已停用");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新凭据失败");
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
          <h1>来源管理</h1>
          <p className="description">管理 RSS、GitHub、HN、arXiv、Product Hunt 和 Hugging Face 数据源。</p>
        </div>
        <button className="ghostButton" type="button" onClick={() => void refresh()}>
          刷新
        </button>
      </section>

      {message ? <section className="infoState">{message}</section> : null}
      {error ? <section className="errorState compact">{error}</section> : null}

      <section className="adminSplit">
        <div className="adminStack">
          <form className="adminForm" onSubmit={handleSubmit}>
            <h2>{editingSource ? "编辑来源" : "新增来源"}</h2>
            {editingSource ? <p className="mutedText">正在编辑：{editingSource.name}</p> : null}
            <label>
              <span>名称</span>
              <input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                placeholder="例如：OpenAI Blog"
                required
              />
            </label>
            <label>
              <span>类型</span>
              <select
                value={form.type}
                onChange={(event) => setForm({ ...form, type: event.target.value })}
                disabled={editingSource !== null}
              >
                {sourceTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>URL</span>
              <input
                value={form.url}
                onChange={(event) => setForm({ ...form, url: event.target.value })}
                placeholder="RSS 地址或来源入口"
              />
            </label>
            <label>
              <span>检索 Query</span>
              <input
                value={form.query}
                onChange={(event) => setForm({ ...form, query: event.target.value })}
                placeholder="例如：AI Agent / all:LLM"
              />
            </label>
            <label>
              <span>凭据</span>
              <select
                value={form.credential_id}
                onChange={(event) => setForm({ ...form, credential_id: event.target.value })}
              >
                <option value="">不使用凭据</option>
                {credentials.map((credential) => (
                  <option key={credential.id} value={credential.id}>
                    {credential.name} / {sourceTypeLabel(credential.source_type)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>环境变量凭据</span>
              <input
                value={form.credential_env_key}
                onChange={(event) => setForm({ ...form, credential_env_key: event.target.value })}
                placeholder="例如：GITHUB_TOKEN"
              />
            </label>
            <div className="formGridTwo">
              <label>
                <span>状态</span>
                <select
                  value={form.status}
                  onChange={(event) => setForm({ ...form, status: event.target.value })}
                >
                  <option value="enabled">启用</option>
                  <option value="disabled">停用</option>
                </select>
              </label>
              <label>
                <span>权重</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={form.weight}
                  onChange={(event) => setForm({ ...form, weight: Number(event.target.value) })}
                />
              </label>
            </div>
            <label>
              <span>单次采集数量</span>
              <input
                type="number"
                min="1"
                max="100"
                value={form.limit}
                onChange={(event) => setForm({ ...form, limit: Number(event.target.value) })}
              />
            </label>
            <label>
              <span>语言</span>
              <input
                value={form.language}
                onChange={(event) => setForm({ ...form, language: event.target.value })}
                placeholder="zh / en"
              />
            </label>
            <button type="submit" disabled={saving}>
              {saving ? "保存中" : editingSource ? "更新来源" : "保存来源"}
            </button>
            {editingSource ? (
              <button className="ghostButton" type="button" onClick={resetEditor}>
                取消编辑
              </button>
            ) : null}
          </form>

          <form className="adminForm" onSubmit={handleCreateCredential}>
            <h2>新增凭据</h2>
            <label>
              <span>名称</span>
              <input
                value={credentialForm.name}
                onChange={(event) => setCredentialForm({ ...credentialForm, name: event.target.value })}
                placeholder="例如：GitHub Token"
                required
              />
            </label>
            <label>
              <span>来源类型</span>
              <select
                value={credentialForm.source_type}
                onChange={(event) =>
                  setCredentialForm({ ...credentialForm, source_type: event.target.value })
                }
              >
                {sourceTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>密钥</span>
              <input
                type="password"
                value={credentialForm.secret}
                onChange={(event) => setCredentialForm({ ...credentialForm, secret: event.target.value })}
                placeholder="保存后只展示脱敏值"
                required
              />
            </label>
            <label>
              <span>状态</span>
              <select
                value={credentialForm.status}
                onChange={(event) => setCredentialForm({ ...credentialForm, status: event.target.value })}
              >
                <option value="active">启用</option>
                <option value="disabled">停用</option>
              </select>
            </label>
            <button type="submit" disabled={savingCredential}>
              {savingCredential ? "保存中" : "保存凭据"}
            </button>
          </form>
        </div>

        <section className="tableWrap">
          {loading ? (
            <div className="emptyState">正在加载来源</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>来源</th>
                  <th>类型</th>
                  <th>状态</th>
                  <th>权重</th>
                  <th>最近抓取</th>
                  <th>凭据</th>
                  <th>错误</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((source) => (
                  <tr key={source.id}>
                    <td>
                      <strong>{source.name}</strong>
                      <br />
                      <span className="mutedText">{source.url || "未配置 URL"}</span>
                    </td>
                    <td>{sourceTypeLabel(source.type)}</td>
                    <td>
                      <span className={`statusBadge ${source.status === "enabled" ? "success" : "failed"}`}>
                        {source.status === "enabled" ? "启用" : source.status}
                      </span>
                    </td>
                    <td>{source.weight}</td>
                    <td>{source.last_fetched_at ? formatDateTime(source.last_fetched_at) : "未抓取"}</td>
                    <td>{credentialName(source.credential_id, credentials) || source.credential_env_key || "无"}</td>
                    <td>{source.last_error || ""}</td>
                    <td>
                      <div className="itemActions">
                        <button className="ghostButton" type="button" onClick={() => startEdit(source)}>
                          编辑
                        </button>
                        <button className="ghostButton" type="button" onClick={() => void toggleStatus(source)}>
                          {source.status === "enabled" ? "停用" : "启用"}
                        </button>
                        <button
                          className="ghostButton"
                          type="button"
                          disabled={collectingSourceId === source.id}
                          onClick={() => void collectSource(source)}
                        >
                          {collectingSourceId === source.id ? "创建中" : "采集"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </section>

      <section className="tableWrap secondaryTable">
        <table>
          <thead>
            <tr>
              <th>凭据</th>
              <th>类型</th>
              <th>状态</th>
              <th>脱敏值</th>
              <th>测试状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {credentials.map((credential) => (
              <tr key={credential.id}>
                <td>{credential.name}</td>
                <td>{sourceTypeLabel(credential.source_type)}</td>
                <td>
                  <span className={`statusBadge ${credential.status === "active" ? "success" : "failed"}`}>
                    {credential.status === "active" ? "启用" : credential.status}
                  </span>
                </td>
                <td>{credential.secret_masked}</td>
                <td>{credential.last_test_status || "未测试"}</td>
                <td>
                  <button
                    className="ghostButton"
                    type="button"
                    onClick={() => void toggleCredentialStatus(credential)}
                  >
                    {credential.status === "active" ? "停用" : "启用"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}

function sourceTypeLabel(value: string) {
  return sourceTypes.find((type) => type.value === value)?.label || value;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function credentialName(credentialId: string | null, credentials: SourceCredential[]) {
  if (!credentialId) {
    return null;
  }
  return credentials.find((credential) => credential.id === credentialId)?.name ?? "已关联凭据";
}
