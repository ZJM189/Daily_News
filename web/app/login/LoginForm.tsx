"use client";

import { ArrowLeft, LockKeyhole, LogIn, ScanLine, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
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
    <main className="loginPage">
      <section className="loginExperience">
        <div className="loginVisual">
          <Link className="loginBackLink" href="/">
            <ArrowLeft size={16} />
            返回公开简报
          </Link>
          <div className="loginVisualGrid" aria-hidden="true" />
          <div className="loginVisualCopy">
            <span className="loginVisualMark">
              <ScanLine size={20} />
            </span>
            <h1>进入你的<br />AI 情报工作区</h1>
            <p>管理采集来源、生成任务和个人收藏，让每天的 AI 信息流更可控。</p>
            <div className="loginFeatureLine">
              <ShieldCheck size={16} />
              <span>权限隔离 · 数据留在你的工作区</span>
            </div>
          </div>
        </div>
        <section className="loginPanel">
          <div className="loginPanelHeader">
            <span className="loginPanelIcon">
              <LockKeyhole size={18} />
            </span>
            <div>
              <p className="eyebrow">DAILY NEWS</p>
              <h2>登录工作区</h2>
              <p className="description">使用管理员创建的账号继续。</p>
            </div>
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
              <LogIn size={16} />
            </button>
          </form>
          <p className="loginPanelFootnote">登录后将根据你的权限进入对应页面。</p>
        </section>
      </section>
    </main>
  );
}

function safeNextPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/today";
  }
  return value;
}
