"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [status, setStatus] = useState("");

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("登入中...");

    try {
      const result = await api.login({ email, password });
      setToken(result.access_token, rememberMe);
      setStatus("登入成功，跳轉中...");
      router.replace("/settings");
    } catch (err) {
      setStatus(`登入失敗：${(err as Error).message}`);
    }
  };

  return (
    <section className="max-w-md mx-auto mt-10 space-y-4">
      <div className="card-surface p-6 space-y-2">
        <span className="brand-pill">Welcome Back</span>
        <h2 className="text-2xl font-bold">登入</h2>
        <p className="text-sm text-slate-600">登入後可使用文章生成、提示詞擴寫與自動發布。</p>
      </div>

      <div className="card-surface p-6 space-y-4">
        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm font-medium text-slate-700">
            Email
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </label>

          <label className="block text-sm font-medium text-slate-700">
            密碼
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="輸入你的密碼"
              required
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            記住我（下次免重新登入）
          </label>

          <button type="submit" className="brand-btn w-full px-4 py-2">
            登入
          </button>
        </form>

        {status && <p className="text-sm text-slate-600">{status}</p>}
        <div className="text-sm text-slate-600 space-y-1">
          <p>
            還沒有帳號？
            <Link href="/register" className="ml-1 brand-link">
              前往註冊
            </Link>
          </p>
          <p>
            忘記密碼？
            <Link href="/forgot-password" className="ml-1 brand-link">
              立即重設
            </Link>
          </p>
        </div>
      </div>
    </section>
  );
}
