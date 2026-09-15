"use client";

import { ArrowLeft, Eye, EyeOff, LockKeyhole, LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { AnimatedLoginCharacters } from "./AnimatedLoginCharacters";
import RadarMark from "../components/RadarMark";
import { AppFooter } from "../components/AppFooter";
import { login } from "../../lib/api";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loginSuccess, setLoginSuccess] = useState(false);

  async function submitLogin() {
    setSubmitting(true);
    setError(null);
    try {
      await login(loginName, password);
      setLoginSuccess(true);
      window.setTimeout(() => {
        router.replace(safeNextPath(searchParams.get("next")));
      }, 600);
    } catch (err) {
      setLoginSuccess(false);
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
        <AnimatedLoginCharacters
          isTyping={Boolean(loginName || password)}
          showPassword={showPassword}
          passwordLength={password.length}
          loginFailed={Boolean(error)}
          loginSuccess={loginSuccess}
        />
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
                <div className="loginPasswordField">
                  <input
                    autoComplete="current-password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="请输入密码"
                  />
                  <button
                    className="loginPasswordToggle"
                    type="button"
                    aria-label={showPassword ? "隐藏密码" : "显示密码"}
                    title={showPassword ? "隐藏密码" : "显示密码"}
                    onClick={() => setShowPassword((visible) => !visible)}
                  >
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
              </label>
            {error ? <div className="errorState compact">{error}</div> : null}
            <button type="submit" disabled={submitting || !loginName || !password}>
              {submitting ? "登录中" : "登录"}
              <LogIn size={16} />
            </button>
          </form>
        </section>
      </main>
      <AppFooter />
    </div>
  );
}

function safeNextPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/today";
  }
  return value;
}
