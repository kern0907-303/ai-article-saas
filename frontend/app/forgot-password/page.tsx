"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useState } from "react";

import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [resetToken, setResetToken] = useState("");

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("送出中...");
    setResetToken("");

    try {
      const result = await api.forgotPassword({ email });
      setStatus(result.message);
      if (result.reset_token) {
        setResetToken(result.reset_token);
      }
    } catch (err) {
      setStatus(`送出失敗：${(err as Error).message}`);
    }
  };

  return (
    <section className="max-w-md mx-auto mt-10 space-y-4">
      <div className="card-surface p-6 space-y-2">
        <span className="brand-pill">Reset Password</span>
        <h2 className="text-2xl font-bold">忘記密碼</h2>
        <p className="text-sm text-slate-600">輸入你的 Email，我們會提供重設密碼連結。</p>
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
              required
            />
          </label>
          <button type="submit" className="brand-btn w-full px-4 py-2">
            送出重設申請
          </button>
        </form>

        {status && <p className="text-sm text-slate-600">{status}</p>}
        {resetToken && (
          <div className="rounded-xl border border-[#c7ebe8] bg-[#f3fbfb] p-3 text-sm space-y-2">
            <p className="font-semibold text-[#0f766e]">測試用重設 Token（正式版請走 Email）</p>
            <code className="block break-all text-xs text-slate-700">{resetToken}</code>
            <Link href={`/reset-password?token=${encodeURIComponent(resetToken)}`} className="brand-link text-xs">
              直接帶入重設頁
            </Link>
          </div>
        )}

        <p className="text-sm text-slate-600">
          返回
          <Link href="/login" className="ml-1 brand-link">
            登入頁
          </Link>
        </p>
      </div>
    </section>
  );
}
