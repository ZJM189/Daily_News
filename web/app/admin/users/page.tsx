"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  CardHeader,
  Notice,
  PageHeader,
  PageScaffold
} from "../../components/UiPrimitives";
import { createUser, listUsers, resetUserPassword, updateUser } from "../../../lib/api";
import type { User } from "../../../lib/types";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetTarget, setResetTarget] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    username: "",
    email: "",
    display_name: "",
    password: "",
    role: "user" as "user" | "admin",
    status: "active" as "active" | "disabled"
  });

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const nextUsers = await listUsers();
      setUsers(nextUsers);
      if (editingUser) {
        setEditingUser(nextUsers.find((user) => user.id === editingUser.id) ?? null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "用户列表加载失败");
    } finally {
      setLoading(false);
    }
  }

  function startEdit(user: User) {
    setEditingUser(user);
    setForm({
      username: "",
      email: "",
      display_name: user.display_name || "",
      password: "",
      role: user.role as "user" | "admin",
      status: user.status as "active" | "disabled"
    });
  }

  function resetEditor() {
    setEditingUser(null);
    setForm({
      username: "",
      email: "",
      display_name: "",
      password: "",
      role: "user",
      status: "active"
    });
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await createUser({
        username: form.username,
        email: form.email || null,
        display_name: form.display_name || null,
        password: form.password,
        role: form.role,
        status: form.status
      });
      setMessage("用户已创建");
      setForm({ ...form, username: "", email: "", display_name: "", password: "" });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建用户失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingUser) {
      return;
    }
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await updateUser(editingUser.id, {
        display_name: form.display_name || null,
        role: form.role,
        status: form.status
      });
      setMessage("用户已更新");
      resetEditor();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新用户失败");
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus(user: User) {
    setMessage(null);
    setError(null);
    try {
      await updateUser(user.id, {
        status: user.status === "active" ? "disabled" : "active"
      });
      setMessage(user.status === "active" ? "用户已禁用" : "用户已启用");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新用户失败");
    }
  }

  async function handleResetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!resetTarget) {
      return;
    }
    setResetting(true);
    setMessage(null);
    setError(null);
    try {
      await resetUserPassword(resetTarget.id, newPassword);
      setMessage(`已重置 ${resetTarget.username} 的密码`);
      setResetTarget(null);
      setNewPassword("");
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
    <PageScaffold>
      <PageHeader
        eyebrow="管理员"
        title="用户管理"
        description="系统不开放注册，所有用户由管理员创建、启停和分配角色。"
        actions={
        <button className="ghostButton" type="button" onClick={() => void refresh()}>
          刷新
        </button>
        }
      />

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="danger" compact>{error}</Notice> : null}

      <section className="adminSplit">
        <div className="adminStack">
          <form className="adminForm" onSubmit={handleCreate}>
            <CardHeader
              title="创建用户"
              description="创建后用户即可用账号密码登录系统。"
            />
            <label>
              <span>用户名</span>
              <input
                value={form.username}
                onChange={(event) => setForm({ ...form, username: event.target.value })}
                placeholder="例如：news_editor"
                required
              />
            </label>
            <label>
              <span>邮箱</span>
              <input
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                placeholder="可选"
              />
            </label>
            <label>
              <span>显示名</span>
              <input
                value={form.display_name}
                onChange={(event) => setForm({ ...form, display_name: event.target.value })}
                placeholder="可选"
              />
            </label>
            <label>
              <span>初始密码</span>
              <input
                type="password"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                placeholder="至少 10 位"
                required
              />
            </label>
            <div className="formGridTwo">
              <label>
                <span>角色</span>
                <select
                  value={form.role}
                  onChange={(event) =>
                    setForm({ ...form, role: event.target.value as "user" | "admin" })
                  }
                >
                  <option value="user">普通用户</option>
                  <option value="admin">管理员</option>
                </select>
              </label>
              <label>
                <span>状态</span>
                <select
                  value={form.status}
                  onChange={(event) =>
                    setForm({ ...form, status: event.target.value as "active" | "disabled" })
                  }
                >
                  <option value="active">启用</option>
                  <option value="disabled">禁用</option>
                </select>
              </label>
            </div>
            <button type="submit" disabled={saving}>
              {saving ? "创建中" : "创建用户"}
            </button>
          </form>

          {editingUser ? (
            <form className="adminForm" onSubmit={handleUpdate}>
              <CardHeader
                title="编辑用户"
                description={editingUser.display_name || editingUser.username}
              />
              <label>
                <span>显示名</span>
                <input
                  value={form.display_name}
                  onChange={(event) => setForm({ ...form, display_name: event.target.value })}
                  placeholder="可选"
                />
              </label>
              <div className="formGridTwo">
                <label>
                  <span>角色</span>
                  <select
                    value={form.role}
                    onChange={(event) =>
                      setForm({ ...form, role: event.target.value as "user" | "admin" })
                    }
                  >
                    <option value="user">普通用户</option>
                    <option value="admin">管理员</option>
                  </select>
                </label>
                <label>
                  <span>状态</span>
                  <select
                    value={form.status}
                    onChange={(event) =>
                      setForm({ ...form, status: event.target.value as "active" | "disabled" })
                    }
                  >
                    <option value="active">启用</option>
                    <option value="disabled">禁用</option>
                  </select>
                </label>
              </div>
              <button type="submit" disabled={saving}>
                {saving ? "保存中" : "保存用户"}
              </button>
              <button className="ghostButton" type="button" onClick={resetEditor}>
                取消编辑
              </button>
            </form>
          ) : null}

          {resetTarget ? (
            <form className="adminForm" onSubmit={handleResetPassword}>
              <CardHeader
                title="重置密码"
                description={resetTarget.display_name || resetTarget.username}
              />
              <label>
                <span>新密码</span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder="至少 10 位"
                  required
                />
              </label>
              <div className="inlineForm">
                <button type="submit" disabled={resetting}>
                  {resetting ? "重置中" : "确认重置"}
                </button>
                <button
                  className="ghostButton"
                  type="button"
                  onClick={() => {
                    setResetTarget(null);
                    setNewPassword("");
                  }}
                >
                  取消
                </button>
              </div>
            </form>
          ) : null}
        </div>

        <section className="tableWrap tableCard">
          <div className="tableCardHeader">
            <h2>用户列表</h2>
            <p className="mutedText">管理账号状态、角色和密码重置。</p>
          </div>
          {loading ? (
            <div className="emptyState">正在加载用户</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>用户</th>
                  <th>角色</th>
                  <th>状态</th>
                  <th>最近登录</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <strong>{user.display_name || user.username}</strong>
                      <br />
                      <span className="mutedText">{user.email || user.username}</span>
                    </td>
                    <td>{user.role === "admin" ? "管理员" : "普通用户"}</td>
                    <td>
                      <span className={`statusBadge ${user.status === "active" ? "success" : "failed"}`}>
                        {user.status === "active" ? "启用" : "禁用"}
                      </span>
                    </td>
                    <td>{user.last_login_at ? formatDateTime(user.last_login_at) : "从未登录"}</td>
                    <td>
                      <div className="itemActions">
                        <button className="ghostButton" type="button" onClick={() => startEdit(user)}>
                          编辑
                        </button>
                        <button className="ghostButton" type="button" onClick={() => void toggleStatus(user)}>
                          {user.status === "active" ? "禁用" : "启用"}
                        </button>
                        <button
                          className="ghostButton"
                          type="button"
                          onClick={() => setResetTarget(user)}
                        >
                          重置密码
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
    </PageScaffold>
  );
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}
