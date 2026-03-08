"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { api } from "@/lib/api";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const tokenFromUrl = useMemo(() => searchParams.get("token") || "", [searchParams]);

  const [token, setToken] = useState(tokenFromUrl);
  const [newPassword, setNewPassword] = useState("");
  const [status, setStatus] = useState("");

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("重設中...");

    try {
      const result = await api.resetPassword({ token, new_password: newPassword });
      setStatus(result.message);
    } catch (err) {
      setStatus(`重設失敗：${(err as Error).message}`);
    }
  };

  return (
    <section className="max-w-md mx-auto mt-10 space-y-4">
      <div className="card-surface p-6 space-y-2">
        <span className="brand-pill">Set New Password</span>
        <h2 className="text-2xl font-bold">重設密碼</h2>
        <p className="text-sm text-slate-600">貼上重設 token，設定新密碼後重新登入。</p>
      </div>

      <div className="card-surface p-6 space-y-4">
        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm font-medium text-slate-700">
            重設 Token
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
            />
          </label>

          <label className="block text-sm font-medium text-slate-700">
            新密碼（至少 8 碼）
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>

          <button type="submit" className="brand-btn w-full px-4 py-2">
            確認重設
          </button>
        </form>

        {status && <p className="text-sm text-slate-600">{status}</p>}
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
