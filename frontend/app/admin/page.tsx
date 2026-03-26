"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { AdminRecentPayment, AdminRecentUser, AdminStats } from "@/lib/types";

const ADMIN_KEY_STORAGE = "admin_api_key";

function money(cents: number, currency = "TWD") {
  return `${(cents / 100).toLocaleString("zh-TW")} ${currency}`;
}

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminRecentUser[]>([]);
  const [payments, setPayments] = useState<AdminRecentPayment[]>([]);
  const [status, setStatus] = useState("請輸入 Admin Key 後載入後台資料");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const cached = localStorage.getItem(ADMIN_KEY_STORAGE);
    if (cached) {
      setAdminKey(cached);
    }
  }, []);

  const load = useCallback(async () => {
    if (!adminKey.trim()) {
      setStatus("請先輸入 Admin Key");
      return;
    }

    setLoading(true);
    setStatus("載入中...");

    try {
      localStorage.setItem(ADMIN_KEY_STORAGE, adminKey.trim());
      const [statsResult, usersResult, paymentsResult] = await Promise.all([
        api.getAdminStats(adminKey.trim()),
        api.listAdminRecentUsers(adminKey.trim(), 12),
        api.listAdminRecentPayments(adminKey.trim(), 12),
      ]);
      setStats(statsResult);
      setUsers(usersResult);
      setPayments(paymentsResult);
      setStatus("載入成功");
    } catch (err) {
      setStatus(`載入失敗：${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [adminKey]);

  const kpis = useMemo(() => {
    if (!stats) return [];
    return [
      { label: "總註冊人數", value: stats.total_users.toLocaleString("zh-TW") },
      { label: "近 7 天新註冊", value: stats.new_users_7d.toLocaleString("zh-TW") },
      { label: "啟用中付費用戶", value: stats.active_paid_users.toLocaleString("zh-TW") },
      { label: "啟用中試用用戶", value: stats.active_trial_users.toLocaleString("zh-TW") },
      { label: "文章總數", value: stats.total_articles.toLocaleString("zh-TW") },
      { label: "近 7 天文章", value: stats.articles_7d.toLocaleString("zh-TW") },
      { label: "知識庫檔案總數", value: stats.total_knowledge_files.toLocaleString("zh-TW") },
      { label: "累積付款筆數", value: stats.total_payments.toLocaleString("zh-TW") },
      { label: "已付款筆數", value: stats.paid_payments.toLocaleString("zh-TW") },
      { label: "累積營收", value: money(stats.paid_revenue_cents) },
    ];
  }, [stats]);

  return (
    <section className="max-w-6xl space-y-5">
      <div className="card-surface p-6 space-y-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="text-2xl font-bold">後台儀表板（第一版）</h2>
          <span className="brand-pill">Admin Analytics</span>
        </div>
        <p className="text-slate-700">提供營運核心數據：註冊、訂閱、內容產出與付款營收。</p>

        <div className="grid md:grid-cols-[1fr_auto_auto] gap-3 items-end">
          <label className="block text-sm font-medium text-slate-700">
            Admin Key
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              placeholder="請輸入 X-Admin-Key"
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
            />
          </label>
          <button className="brand-btn px-4 py-2" onClick={load} disabled={loading}>
            {loading ? "載入中..." : "載入統計"}
          </button>
          <button
            className="brand-btn-secondary px-4 py-2"
            onClick={() => {
              localStorage.removeItem(ADMIN_KEY_STORAGE);
              setAdminKey("");
              setStats(null);
              setUsers([]);
              setPayments([]);
              setStatus("已清除本機 Admin Key");
            }}
            disabled={loading}
          >
            清除 Key
          </button>
        </div>

        <p className="text-sm text-slate-600">{status}</p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-3">
        {kpis.map((item) => (
          <div key={item.label} className="card-surface p-4">
            <p className="text-xs text-slate-500">{item.label}</p>
            <p className="mt-1 text-xl font-bold text-[var(--text)]">{item.value}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card-surface p-5 space-y-3">
          <h3 className="text-lg font-semibold">近期註冊用戶</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-[var(--line)]">
                  <th className="py-2 pr-3">ID</th>
                  <th className="py-2 pr-3">Email</th>
                  <th className="py-2">註冊時間</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-slate-100 text-slate-700">
                    <td className="py-2 pr-3">{u.id}</td>
                    <td className="py-2 pr-3">{u.email}</td>
                    <td className="py-2">{new Date(u.created_at).toLocaleString("zh-TW")}</td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td className="py-3 text-slate-500" colSpan={3}>
                      尚無資料
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card-surface p-5 space-y-3">
          <h3 className="text-lg font-semibold">近期付款紀錄</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-[var(--line)]">
                  <th className="py-2 pr-3">交易</th>
                  <th className="py-2 pr-3">用戶</th>
                  <th className="py-2 pr-3">方案</th>
                  <th className="py-2 pr-3">金額</th>
                  <th className="py-2">狀態</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((p) => (
                  <tr key={p.payment_id} className="border-b border-slate-100 text-slate-700">
                    <td className="py-2 pr-3">#{p.payment_id}</td>
                    <td className="py-2 pr-3">{p.user_email || `user_${p.user_id}`}</td>
                    <td className="py-2 pr-3">{p.plan_code || "-"}</td>
                    <td className="py-2 pr-3">{money(p.amount_cents, p.currency)}</td>
                    <td className="py-2">{p.status}</td>
                  </tr>
                ))}
                {payments.length === 0 && (
                  <tr>
                    <td className="py-3 text-slate-500" colSpan={5}>
                      尚無資料
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
