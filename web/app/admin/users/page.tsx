"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  UserCheck,
  UserRound,
  Users
} from "lucide-react";
import {
  AdminEmptyState,
  AdminMetric,
  AdminStatusBadge
} from "../../components/AdminPrimitives";
import { Modal } from "../../components/Modal";
import { Notice, PageHeader, PageScaffold } from "../../components/UiPrimitives";
import { createUser, listUsers, resetUserPassword, updateUser } from "../../../lib/api";
import type { User } from "../../../lib/types";

type UserForm = {
  username: string;
  email: string;
  display_name: string;
  password: string;
  role: "user" | "admin";
  status: "active" | "disabled";
};

const emptyForm: UserForm = {
  username: "",
  email: "",
  display_name: "",
  password: "",
  role: "user",
  status: "active"
};

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [form, setForm] = useState<UserForm>(emptyForm);

  const filteredUsers = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return users.filter((user) => {
      const matchesKeyword =
        !keyword ||
        user.username.toLowerCase().includes(keyword) ||
        (user.display_name || "").toLowerCase().includes(keyword) ||
        (user.email || "").toLowerCase().includes(keyword);
      const matchesRole = roleFilter === "all" || user.role === roleFilter;
      const matchesStatus = statusFilter === "all" || user.status === statusFilter;
      return matchesKeyword && matchesRole && matchesStatus;
    });
  }, [roleFilter, search, statusFilter, users]);

  const activeCount = users.filter((user) => user.status === "active").length;
  const adminCount = users.filter((user) => user.role === "admin").length;
  const signedInCount = users.filter((user) => user.last_login_at).length;

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const nextUsers = await listUsers();
      setUsers(nextUsers);
    } catch (err) {
      setError(err instanceof Error ? err.message : "用户列表加载失败");
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setEditingUser(null);
    setForm(emptyForm);
    setEditorOpen(true);
  }

  function startEdit(user: User) {
    setEditingUser(user);
    setForm(formFromUser(user));
    setEditorOpen(true);
  }

  function closeEditor() {
    setEditorOpen(false);
    setEditingUser(null);
    setForm(emptyForm);
  }

  function openPasswordReset(user: User) {
    setResetTarget(user);
    setNewPassword("");
  }

  function closePasswordReset() {
    setResetTarget(null);
    setNewPassword("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      if (editingUser) {
        await updateUser(editingUser.id, {
          display_name: form.display_name || null,
          role: form.role,
          status: form.status
        });
        setMessage("用户已更新");
      } else {
        await createUser({
          username: form.username,
          email: form.email || null,
          display_name: form.display_name || null,
          password: form.password,
          role: form.role,
          status: form.status
        });
        setMessage("用户已创建");
      }
      closeEditor();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : editingUser ? "更新用户失败" : "创建用户失败");
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus(user: User) {
    setMessage(null);
    setError(null);
    try {
      const nextStatus = user.status === "active" ? "disabled" : "active";
      await updateUser(user.id, { status: nextStatus });
      setMessage(nextStatus === "active" ? "用户已启用" : "用户已禁用");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新用户失败");
    }
  }

  async function handleResetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!resetTarget) return;
    setResetting(true);
    setMessage(null);
    setError(null);
    try {
      await resetUserPassword(resetTarget.id, newPassword);
      setMessage(`已重置 ${resetTarget.username} 的密码`);
      closePasswordReset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "重置密码失败");
    } finally {
      setResetting(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <PageScaffold className="managementPage">
      <PageHeader
        eyebrow="管理员 / 账号权限"
        title="用户管理"
        description="管理系统账号、访问状态和管理员权限。"
        actions={
          <div className="managementPageActions">
            <button className="ghostButton" type="button" onClick={() => void refresh()} title="刷新列表"><RefreshCw size={16} aria-hidden="true" />刷新</button>
            <button type="button" onClick={openCreate}><Plus size={17} aria-hidden="true" />新增用户</button>
          </div>
        }
      />

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="danger" compact>{error}</Notice> : null}

      <section className="managementMetricStrip" aria-label="用户摘要">
        <AdminMetric icon={<Users size={18} />} label="用户总数" value={users.length} detail="系统内全部账号" />
        <AdminMetric icon={<UserCheck size={18} />} label="启用账号" value={activeCount} detail={`${users.length - activeCount} 个已停用`} tone="success" />
        <AdminMetric icon={<ShieldCheck size={18} />} label="管理员" value={adminCount} detail="拥有系统管理权限" />
        <AdminMetric icon={<KeyRound size={18} />} label="已有登录" value={signedInCount} detail="至少成功登录一次" />
      </section>

      <section className="managementWorkspace">
        <div className="managementToolbar">
          <div className="managementToolbarTitle">
            <div><h2>用户列表</h2><p>查看账号身份、角色、状态和最近登录时间。</p></div>
            <span className="managementResultCount">{filteredUsers.length} / {users.length}</span>
          </div>
          <div className="managementFilters">
            <label className="managementSearchField"><Search size={16} aria-hidden="true" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索用户名、显示名或邮箱" /></label>
            <label className="managementFilterSelect"><select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} aria-label="筛选用户角色"><option value="all">全部角色</option><option value="admin">管理员</option><option value="user">普通用户</option></select><ChevronDown size={15} aria-hidden="true" /></label>
            <label className="managementFilterSelect"><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="筛选用户状态"><option value="all">全部状态</option><option value="active">启用</option><option value="disabled">停用</option></select><ChevronDown size={15} aria-hidden="true" /></label>
          </div>
        </div>

        {loading ? (
          <AdminEmptyState icon={<RefreshCw className="spin" size={20} />} title="正在加载用户" />
        ) : filteredUsers.length ? (
          <div className="managementTableWrap">
            <table className="managementTable userManagementTable">
              <thead><tr><th>用户</th><th>角色</th><th>状态</th><th>最近登录</th><th>操作</th></tr></thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr key={user.id}>
                    <td><div className="managementNameCell"><span className="managementIdentityMark managementAvatar">{userInitial(user)}</span><div><strong>{user.display_name || user.username}</strong><small>{user.email || `@${user.username}`}</small></div></div></td>
                    <td><span className="managementSecondaryText">{user.role === "admin" ? "管理员" : "普通用户"}</span></td>
                    <td><AdminStatusBadge tone={user.status === "active" ? "success" : "neutral"}>{user.status === "active" ? "启用" : "停用"}</AdminStatusBadge></td>
                    <td><span className="managementSecondaryText">{user.last_login_at ? formatDateTime(user.last_login_at) : "从未登录"}</span></td>
                    <td><div className="managementRowActions"><button className="iconAction" type="button" title="编辑用户" aria-label={`编辑 ${user.username}`} onClick={() => startEdit(user)}><Pencil size={15} /></button><button className="iconAction" type="button" title="重置密码" aria-label={`重置 ${user.username} 的密码`} onClick={() => openPasswordReset(user)}><KeyRound size={15} /></button><button className="textAction" type="button" onClick={() => void toggleStatus(user)}>{user.status === "active" ? "停用" : "启用"}</button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <AdminEmptyState icon={<UserRound size={22} />} title="没有匹配的用户" description="调整筛选条件，或新增一个账号。" />
        )}
      </section>

      {editorOpen ? (
        <Modal title={editingUser ? "编辑用户" : "新增用户"} onClose={closeEditor} busy={saving} drawer>
          <form className="managementEditorForm" onSubmit={handleSubmit}>
            <p className="modalIntro">{editingUser ? `更新「${editingUser.username}」的账号信息。` : "创建一个可登录 Daily News 的系统账号。"}</p>
            {!editingUser ? <><label><span>用户名</span><input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} placeholder="例如：news_editor" required /></label><label><span>邮箱 <small>可选</small></span><input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="name@example.com" /></label></> : null}
            <label><span>显示名 <small>可选</small></span><input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} placeholder="用于界面展示" /></label>
            {!editingUser ? <label><span>初始密码</span><input type="password" minLength={10} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="至少 10 位" required /></label> : null}
            <div className="formGridTwo"><label><span>角色</span><select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as UserForm["role"] })}><option value="user">普通用户</option><option value="admin">管理员</option></select></label><label><span>状态</span><select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as UserForm["status"] })}><option value="active">启用</option><option value="disabled">停用</option></select></label></div>
            <div className="modalActions"><button className="ghostButton" type="button" onClick={closeEditor}>取消</button><button type="submit" disabled={saving}>{saving ? "保存中" : editingUser ? "保存修改" : "创建用户"}</button></div>
          </form>
        </Modal>
      ) : null}

      {resetTarget ? (
        <Modal title="重置密码" onClose={closePasswordReset} busy={resetting}>
          <form className="managementEditorForm managementDialogForm" onSubmit={handleResetPassword}>
            <p className="modalIntro">为「{resetTarget.display_name || resetTarget.username}」设置新密码。</p>
            <label><span>新密码</span><input type="password" minLength={10} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="至少 10 位" required autoFocus /></label>
            <div className="modalActions"><button className="ghostButton" type="button" onClick={closePasswordReset}>取消</button><button type="submit" disabled={resetting}>{resetting ? "重置中" : "确认重置"}</button></div>
          </form>
        </Modal>
      ) : null}
    </PageScaffold>
  );
}

function formFromUser(user: User): UserForm {
  return { username: user.username, email: user.email || "", display_name: user.display_name || "", password: "", role: user.role, status: user.status };
}

function userInitial(user: User) {
  return (user.display_name || user.username).trim().slice(0, 1).toUpperCase();
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}
