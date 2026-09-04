"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { login } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitLogin() {
    setSubmitting(true);
    setError(null);
    try {
      await login(loginName, password);
      router.replace("/today");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="loginPage">
      <section className="loginPanel">
        <div>
          <p className="eyebrow">Daily News</p>
          <h1>登录 AI 热点看板</h1>
          <p className="description">使用管理员创建的账号进入系统。</p>
        </div>
        <form
          className="loginForm"
          onSubmit={(event) => {
            event.preventDefault();
            void submitLogin();
          }}
        >
          <label>
            <span>账号或邮箱</span>
            <input
              autoComplete="username"
              value={loginName}
              onChange={(event) => setLoginName(event.target.value)}
              placeholder="admin"
            />
          </label>
          <label>
            <span>密码</span>
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="请输入密码"
            />
          </label>
          {error ? <div className="errorState compact">{error}</div> : null}
          <button type="submit" disabled={submitting || !loginName || !password}>
            {submitting ? "登录中" : "登录"}
          </button>
        </form>
      </section>
    </main>
  );
}
