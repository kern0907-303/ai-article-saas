"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("註冊中...");

    try {
      const result = await api.register({ email, password });
      setToken(result.access_token);
      setStatus("註冊成功，跳轉中...");
      router.replace("/settings");
    } catch (err) {
      setStatus(`註冊失敗：${(err as Error).message}`);
    }
  };

  return (
    <section className="max-w-md mx-auto mt-10 space-y-4">
      <div className="card-surface p-6 space-y-2">
        <span className="brand-pill">Create Account</span>
        <h2 className="text-2xl font-bold">註冊</h2>
        <p className="text-sm text-slate-600">建立帳號後即可開始你的 AI 內容工作流程。</p>
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
            密碼（至少 8 碼）
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 8 碼，建議含英文與符號"
              required
              minLength={8}
            />
          </label>

          <button type="submit" className="brand-btn w-full px-4 py-2">
            註冊
          </button>
        </form>

        {status && <p className="text-sm text-slate-600">{status}</p>}
        <p className="text-sm text-slate-600">
          已有帳號？
          <Link href="/login" className="ml-1 brand-link">
            前往登入
          </Link>
        </p>
      </div>
    </section>
  );
}
