"use client";

import { FormEvent, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Database,
  KeyRound,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal
} from "lucide-react";
import { Modal } from "../../components/Modal";
import { Notice, PageHeader, PageScaffold } from "../../components/UiPrimitives";
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

type ViewMode = "sources" | "credentials";

const emptySourceForm = {
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
};

export default function AdminSourcesPage() {
  const [view, setView] = useState<ViewMode>("sources");
  const [sources, setSources] = useState<Source[]>([]);
  const [credentials, setCredentials] = useState<SourceCredential[]>([]);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [sourceForm, setSourceForm] = useState(emptySourceForm);
  const [credentialForm, setCredentialForm] = useState({
    name: "",
    source_type: "rss",
    secret: "",
    status: "active"
  });
  const [sourceModalOpen, setSourceModalOpen] = useState(false);
  const [credentialModalOpen, setCredentialModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingCredential, setSavingCredential] = useState(false);
  const [collectingSourceId, setCollectingSourceId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [nextSources, nextCredentials] = await Promise.all([listSources(), listSourceCredentials()]);
      setSources(nextSources);
      setCredentials(nextCredentials);
      if (editingSource) {
        const nextEditing = nextSources.find((source) => source.id === editingSource.id) ?? null;
        if (nextEditing) {
          setEditingSource(nextEditing);
          setSourceForm(formFromSource(nextEditing));
        } else {
          closeSourceModal();
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "来源加载失败");
    } finally {
      setLoading(false);
    }
  }

  const filteredSources = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return sources.filter((source) => {
      const matchesKeyword =
        !keyword ||
        source.name.toLowerCase().includes(keyword) ||
        (source.url || "").toLowerCase().includes(keyword);
      const matchesType = typeFilter === "all" || source.type === typeFilter;
      const matchesStatus = statusFilter === "all" || source.status === statusFilter;
      return matchesKeyword && matchesType && matchesStatus;
    });
  }, [search, sources, statusFilter, typeFilter]);

  const enabledSources = sources.filter((source) => source.status === "enabled").length;
  const errorSources = sources.filter((source) => source.status === "error" || source.last_error).length;
  const activeCredentials = credentials.filter((credential) => credential.status === "active").length;

  function openCreateSource() {
    setEditingSource(null);
    setSourceForm(emptySourceForm);
    setSourceModalOpen(true);
  }

  function openEditSource(source: Source) {
    setEditingSource(source);
    setSourceForm(formFromSource(source));
    setSourceModalOpen(true);
  }

  function closeSourceModal() {
    setSourceModalOpen(false);
    setEditingSource(null);
    setSourceForm(emptySourceForm);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const queryConfig: Record<string, unknown> = {};
      if (sourceForm.query) {
        queryConfig[sourceForm.type === "arxiv" ? "search_query" : "query"] = sourceForm.query;
      }
      if (sourceForm.limit) queryConfig.limit = sourceForm.limit;
      if (editingSource) {
        await updateSource(editingSource.id, {
          name: sourceForm.name,
          status: sourceForm.status,
          url: sourceForm.url || null,
          query_config: queryConfig,
          credential_id: sourceForm.credential_id || null,
          credential_env_key: sourceForm.credential_env_key || null,
          weight: sourceForm.weight,
          language: sourceForm.language || null
        });
        setMessage("来源已更新");
      } else {
        await createSource({
          name: sourceForm.name,
          type: sourceForm.type,
          status: sourceForm.status,
          url: sourceForm.url || null,
          query_config: queryConfig,
          credential_id: sourceForm.credential_id || null,
          credential_env_key: sourceForm.credential_env_key || null,
          weight: sourceForm.weight,
          language: sourceForm.language || null
        });
        setMessage("来源已创建");
      }
      closeSourceModal();
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
      setCredentialModalOpen(false);
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
    <PageScaffold className="sourceAdminPage">
      <PageHeader
        eyebrow="管理员 / 数据接入"
        title="来源管理"
        description="统一管理采集来源和访问凭据，控制哪些内容进入信息库。"
        actions={
          <div className="sourcePageActions">
            <button className="ghostButton" type="button" onClick={() => void refresh()} title="刷新列表">
              <RefreshCw size={16} aria-hidden="true" />
              刷新
            </button>
            <button type="button" onClick={view === "sources" ? openCreateSource : () => setCredentialModalOpen(true)}>
              <Plus size={17} aria-hidden="true" />
              {view === "sources" ? "新增来源" : "新增凭据"}
            </button>
          </div>
        }
      />

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="danger" compact>{error}</Notice> : null}

      <section className="sourceMetricStrip" aria-label="来源概览">
        <Metric icon={<Database size={18} />} label="全部来源" value={sources.length} detail={`${enabledSources} 个正在采集`} />
        <Metric icon={<CheckCircle2 size={18} />} label="启用来源" value={enabledSources} detail="会进入采集任务" />
        <Metric icon={<KeyRound size={18} />} label="可用凭据" value={activeCredentials} detail={`${credentials.length} 个已配置`} />
        <Metric icon={<CircleAlert size={18} />} label="需要关注" value={errorSources} detail={errorSources ? "存在错误或失败" : "当前没有异常"} danger={errorSources > 0} />
      </section>

      <section className="sourceWorkspace">
        <nav className="sourceTabs" aria-label="来源管理视图">
          <button className={view === "sources" ? "active" : ""} type="button" onClick={() => setView("sources")}>
            <Database size={16} aria-hidden="true" /> 数据源 <span>{sources.length}</span>
          </button>
          <button className={view === "credentials" ? "active" : ""} type="button" onClick={() => setView("credentials")}>
            <KeyRound size={16} aria-hidden="true" /> 凭据 <span>{credentials.length}</span>
          </button>
        </nav>

        {view === "sources" ? (
          <section className="sourceListPanel">
            <div className="sourceToolbar">
              <div className="sourceToolbarTitle">
                <div>
                  <h2>数据源</h2>
                  <p>按来源逐个查看状态、配置和采集动作。</p>
                </div>
                <span className="resultCount">{filteredSources.length} / {sources.length}</span>
              </div>
              <div className="sourceFilters">
                <label className="searchField">
                  <Search size={16} aria-hidden="true" />
                  <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索名称或 URL" />
                </label>
                <label className="filterSelect">
                  <SlidersHorizontal size={15} aria-hidden="true" />
                  <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} aria-label="筛选来源类型">
                    <option value="all">全部类型</option>
                    {sourceTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
                  </select>
                  <ChevronDown size={15} aria-hidden="true" />
                </label>
                <label className="filterSelect">
                  <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="筛选来源状态">
                    <option value="all">全部状态</option>
                    <option value="enabled">启用</option>
                    <option value="disabled">停用</option>
                    <option value="error">错误</option>
                  </select>
                  <ChevronDown size={15} aria-hidden="true" />
                </label>
              </div>
            </div>
            <SourceTable
              sources={filteredSources}
              credentials={credentials}
              loading={loading}
              collectingSourceId={collectingSourceId}
              onEdit={openEditSource}
              onToggle={toggleStatus}
              onCollect={collectSource}
            />
          </section>
        ) : (
          <CredentialPanel
            credentials={credentials}
            loading={loading}
            onCreate={() => setCredentialModalOpen(true)}
            onToggle={toggleCredentialStatus}
          />
        )}
      </section>

      {sourceModalOpen ? (
        <Modal title={editingSource ? "编辑来源" : "新增来源"} onClose={closeSourceModal} busy={saving} drawer>
          <form className="sourceEditorForm" onSubmit={handleSubmit}>
            <p className="modalIntro">{editingSource ? `更新「${editingSource.name}」的采集配置。` : "配置一个可被任务调度采集的数据来源。"}</p>
            <label><span>来源名称</span><input value={sourceForm.name} onChange={(event) => setSourceForm({ ...sourceForm, name: event.target.value })} placeholder="例如：OpenAI Blog" required /></label>
            <div className="formGridTwo">
              <label><span>来源类型</span><select value={sourceForm.type} onChange={(event) => setSourceForm({ ...sourceForm, type: event.target.value })} disabled={editingSource !== null}>{sourceTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select></label>
              <label><span>状态</span><select value={sourceForm.status} onChange={(event) => setSourceForm({ ...sourceForm, status: event.target.value })}><option value="enabled">启用</option><option value="disabled">停用</option></select></label>
            </div>
            <label><span>URL</span><input value={sourceForm.url} onChange={(event) => setSourceForm({ ...sourceForm, url: event.target.value })} placeholder="RSS 地址或来源入口" /></label>
            <label><span>检索 Query <small>可选</small></span><input value={sourceForm.query} onChange={(event) => setSourceForm({ ...sourceForm, query: event.target.value })} placeholder="例如：AI Agent / all:LLM" /></label>
            <div className="formGridTwo">
              <label><span>单次采集数量</span><input type="number" min="1" max="100" value={sourceForm.limit} onChange={(event) => setSourceForm({ ...sourceForm, limit: Number(event.target.value) })} /></label>
              <label><span>来源权重</span><input type="number" min="0" max="100" value={sourceForm.weight} onChange={(event) => setSourceForm({ ...sourceForm, weight: Number(event.target.value) })} /></label>
            </div>
            <label><span>关联凭据 <small>可选</small></span><select value={sourceForm.credential_id} onChange={(event) => setSourceForm({ ...sourceForm, credential_id: event.target.value })}><option value="">不使用凭据</option>{credentials.filter((credential) => credential.source_type === sourceForm.type).map((credential) => <option key={credential.id} value={credential.id}>{credential.name} · {credential.secret_masked}</option>)}</select></label>
            <label><span>环境变量凭据 <small>可选</small></span><input value={sourceForm.credential_env_key} onChange={(event) => setSourceForm({ ...sourceForm, credential_env_key: event.target.value })} placeholder="例如：GITHUB_TOKEN" /></label>
            <label><span>内容语言</span><input value={sourceForm.language} onChange={(event) => setSourceForm({ ...sourceForm, language: event.target.value })} placeholder="zh / en" /></label>
            <div className="modalActions"><button className="ghostButton" type="button" onClick={closeSourceModal}>取消</button><button type="submit" disabled={saving}>{saving ? "保存中" : editingSource ? "保存修改" : "创建来源"}</button></div>
          </form>
        </Modal>
      ) : null}

      {credentialModalOpen ? (
        <Modal title="新增凭据" onClose={() => setCredentialModalOpen(false)} busy={savingCredential} drawer>
          <form className="sourceEditorForm" onSubmit={handleCreateCredential}>
            <p className="modalIntro">凭据只用于访问需要授权的来源，保存后仅显示脱敏值。</p>
            <label><span>凭据名称</span><input value={credentialForm.name} onChange={(event) => setCredentialForm({ ...credentialForm, name: event.target.value })} placeholder="例如：GitHub Token" required /></label>
            <label><span>来源类型</span><select value={credentialForm.source_type} onChange={(event) => setCredentialForm({ ...credentialForm, source_type: event.target.value })}>{sourceTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select></label>
            <label><span>密钥</span><input type="password" value={credentialForm.secret} onChange={(event) => setCredentialForm({ ...credentialForm, secret: event.target.value })} placeholder="保存后只展示脱敏值" required /></label>
            <label><span>初始状态</span><select value={credentialForm.status} onChange={(event) => setCredentialForm({ ...credentialForm, status: event.target.value })}><option value="active">启用</option><option value="disabled">停用</option></select></label>
            <div className="modalActions"><button className="ghostButton" type="button" onClick={() => setCredentialModalOpen(false)}>取消</button><button type="submit" disabled={savingCredential}>{savingCredential ? "保存中" : "创建凭据"}</button></div>
          </form>
        </Modal>
      ) : null}
    </PageScaffold>
  );
}

function Metric({ icon, label, value, detail, danger = false }: { icon: ReactNode; label: string; value: number; detail: string; danger?: boolean }) {
  return <div className={`sourceMetric ${danger ? "danger" : ""}`}><span className="sourceMetricIcon">{icon}</span><div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div></div>;
}

function SourceTable({ sources, credentials, loading, collectingSourceId, onEdit, onToggle, onCollect }: { sources: Source[]; credentials: SourceCredential[]; loading: boolean; collectingSourceId: string | null; onEdit: (source: Source) => void; onToggle: (source: Source) => void; onCollect: (source: Source) => void }) {
  if (loading) return <div className="sourceEmptyState"><RefreshCw className="spin" size={18} />正在加载来源</div>;
  if (!sources.length) return <div className="sourceEmptyState"><Database size={22} /><strong>没有匹配的数据源</strong><span>调整筛选条件，或创建一个新的来源。</span></div>;
  return <div className="sourceTableWrap"><table className="sourceTable"><thead><tr><th>来源</th><th>类型</th><th>状态</th><th>配置</th><th>最近采集</th><th>操作</th></tr></thead><tbody>{sources.map((source) => <tr key={source.id}><td><div className="sourceNameCell"><span className={`sourceTypeMark type-${source.type}`}><Database size={16} /></span><div><strong>{source.name}</strong><small>{source.url || "未配置 URL"}</small></div></div></td><td><span className="typeLabel">{sourceTypeLabel(source.type)}</span></td><td><StatusBadge status={source.status} /></td><td><div className="configSummary"><span>权重 {source.weight}</span><span>{credentialName(source.credential_id, credentials) || source.credential_env_key || "无凭据"}</span></div></td><td><span className="lastCollected">{source.last_fetched_at ? formatDateTime(source.last_fetched_at) : "尚未采集"}</span>{source.last_error ? <small className="tableError" title={source.last_error}><CircleAlert size={13} />采集异常</small> : null}</td><td><div className="sourceRowActions"><button className="iconAction" type="button" title="立即采集" aria-label={`采集 ${source.name}`} disabled={collectingSourceId === source.id} onClick={() => onCollect(source)}><Play size={15} fill="currentColor" /></button><button className="iconAction" type="button" title="编辑来源" aria-label={`编辑 ${source.name}`} onClick={() => onEdit(source)}><Pencil size={15} /></button><button className="textAction" type="button" onClick={() => onToggle(source)}>{source.status === "enabled" ? "停用" : "启用"}</button></div></td></tr>)}</tbody></table></div>;
}

function CredentialPanel({ credentials, loading, onCreate, onToggle }: { credentials: SourceCredential[]; loading: boolean; onCreate: () => void; onToggle: (credential: SourceCredential) => void }) {
  return <section className="sourceListPanel"><div className="sourceToolbar"><div className="sourceToolbarTitle"><div><h2>访问凭据</h2><p>集中管理 API Token，明文密钥不会在页面展示。</p></div></div><button className="compactPrimary" type="button" onClick={onCreate}><Plus size={16} />新增凭据</button></div>{loading ? <div className="sourceEmptyState"><RefreshCw className="spin" size={18} />正在加载凭据</div> : credentials.length ? <div className="credentialGrid">{credentials.map((credential) => <article className="credentialCard" key={credential.id}><div className="credentialCardTop"><span className="credentialIcon"><KeyRound size={17} /></span><StatusBadge status={credential.status} credential /></div><h3>{credential.name}</h3><p>{sourceTypeLabel(credential.source_type)} · {credential.secret_masked}</p><div className="credentialCardMeta"><span>测试状态</span><strong>{credential.last_test_status || "未测试"}</strong></div><button className="ghostButton" type="button" onClick={() => onToggle(credential)}>{credential.status === "active" ? "停用凭据" : "启用凭据"}</button></article>)}</div> : <div className="sourceEmptyState"><KeyRound size={22} /><strong>还没有凭据</strong><span>为需要授权的来源创建访问凭据。</span></div>}</section>;
}

function StatusBadge({ status, credential = false }: { status: string; credential?: boolean }) {
  const label = status === "enabled" || status === "active" ? "正常" : status === "disabled" ? "已停用" : status === "error" ? "错误" : status;
  return <span className={`sourceStatusBadge ${status === "enabled" || status === "active" ? "ok" : status === "error" ? "error" : "off"}`}><span className="statusDot" />{credential && status === "active" ? "可用" : label}</span>;
}

function formFromSource(source: Source) {
  const queryConfig = source.query_config ?? {};
  return {
    name: source.name,
    type: source.type,
    status: source.status,
    url: source.url || "",
    query: typeof queryConfig.search_query === "string" ? queryConfig.search_query : typeof queryConfig.query === "string" ? queryConfig.query : "",
    limit: typeof queryConfig.limit === "number" ? queryConfig.limit : Number.isFinite(Number(queryConfig.limit)) ? Number(queryConfig.limit) : 30,
    weight: source.weight,
    language: source.language || "zh",
    credential_id: source.credential_id || "",
    credential_env_key: source.credential_env_key || ""
  };
}

function sourceTypeLabel(value: string) {
  return sourceTypes.find((type) => type.value === value)?.label || value;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function credentialName(credentialId: string | null, credentials: SourceCredential[]) {
  if (!credentialId) return null;
  return credentials.find((credential) => credential.id === credentialId)?.name ?? "已关联凭据";
}
