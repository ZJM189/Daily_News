"use client";

import { ArrowLeft, LockKeyhole, LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import RadarMark from "../components/RadarMark";
import { login } from "../../lib/api";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitLogin() {
    setSubmitting(true);
    setError(null);
    try {
      await login(loginName, password);
      router.replace(safeNextPath(searchParams.get("next")));
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="loginPage">
      <header className="loginTopbar">
        <div className="loginTopbarInner">
          <Link className="loginBrandLink" href="/">
            <RadarMark />
            <span>每日 AI 简报</span>
          </Link>
          <Link className="loginBackLink" href="/">
            <ArrowLeft size={16} />
            返回公开简报
          </Link>
        </div>
      </header>
      <main className="loginMain">
        <section className="loginPanel" aria-labelledby="login-title">
          <div className="loginPanelHeader">
            <span className="loginPanelIcon">
              <LockKeyhole size={18} />
            </span>
            <h1 id="login-title">登录工作区</h1>
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
                placeholder="请输入账号或邮箱"
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
              <LogIn size={16} />
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}

function safeNextPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/today";
  }
  return value;
}
