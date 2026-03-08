"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { CheckoutResponse, Entitlements, Plan, Subscription } from "@/lib/types";

export default function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [checkout, setCheckout] = useState<CheckoutResponse | null>(null);
  const [status, setStatus] = useState("");

  const load = async () => {
    const [planList, sub, ent] = await Promise.all([api.listPlans(), api.getSubscription(), api.getEntitlements()]);
    setPlans(planList);
    setSubscription(sub);
    setEntitlements(ent);
  };

  useEffect(() => {
    load().catch((err: Error) => setStatus(`載入失敗：${err.message}`));
  }, []);

  const createCheckout = async (planCode: string) => {
    setStatus("建立付款中...");
    try {
      const result = await api.createCheckout({ plan_code: planCode, provider: "mockpay" });
      setCheckout(result);
      setStatus("已建立付款單，請點擊下方『模擬付款成功』完成開通一年權限。");
    } catch (err) {
      setStatus(`建立付款失敗：${(err as Error).message}`);
    }
  };

  const startTrial = async () => {
    setStatus("啟用試用中...");
    try {
      const result = await api.startTrial();
      setStatus(`${result.message}，到期：${new Date(result.expires_at).toLocaleString("zh-TW")}`);
      await load();
    } catch (err) {
      setStatus(`啟用試用失敗：${(err as Error).message}`);
    }
  };

  const markPaid = async () => {
    if (!checkout) return;
    setStatus("更新付款狀態中...");
    try {
      const result = await api.mockMarkPaid({ txn_id: checkout.txn_id, status: "paid" });
      setStatus(result.message);
      await load();
    } catch (err) {
      setStatus(`付款更新失敗：${(err as Error).message}`);
    }
  };

  return (
    <section className="max-w-4xl space-y-5">
      <div className="card-surface p-6 space-y-2">
        <span className="brand-pill">Billing</span>
        <h2 className="text-2xl font-bold">訂閱與付款</h2>
        <p className="text-slate-700">未付款可瀏覽系統；啟用 7 天試用或完成年繳後才能使用 AI 生成功能。</p>
      </div>

      <div className="card-surface p-6 space-y-3">
        <h3 className="text-lg font-semibold">目前訂閱狀態</h3>
        {subscription ? (
          <div className="text-sm text-slate-700 space-y-1">
            <p>狀態：{subscription.status}</p>
            <p>層級：{subscription.access_tier}</p>
            <p>方案：{subscription.plan_code || "未開通"}</p>
            <p>到期日：{subscription.expires_at || "-"}</p>
            <p>可用：{subscription.is_active ? "是" : "否"}</p>
          </div>
        ) : (
          <p className="text-sm text-slate-600">載入中...</p>
        )}
      </div>

      <div className="card-surface p-6 space-y-3">
        <h3 className="text-lg font-semibold">試用權限</h3>
        {entitlements ? (
          <div className="text-sm text-slate-700 space-y-1">
            <p>試用是否已用過：{entitlements.trial_used ? "是" : "否"}</p>
            <p>今日文章生成剩餘：{entitlements.remaining.article_generate_today ?? "-"}</p>
            <p>今日提示詞擴寫剩餘：{entitlements.remaining.prompt_expand_today ?? "-"}</p>
            <p>今日圖片生成剩餘：{entitlements.remaining.image_generate_today ?? "-"}</p>
            <p>
              知識庫剩餘容量：
              {entitlements.remaining.knowledge_total_bytes >= 0
                ? `${Math.floor((entitlements.remaining.knowledge_total_bytes / 1024 / 1024) * 10) / 10} MB`
                : "無上限"}
            </p>
          </div>
        ) : (
          <p className="text-sm text-slate-600">載入中...</p>
        )}

        <button
          className="brand-btn-secondary px-4 py-2 disabled:opacity-60 disabled:cursor-not-allowed"
          onClick={startTrial}
          disabled={!!(entitlements?.trial_used || subscription?.access_tier === "paid")}
        >
          啟用 7 天試用
        </button>
      </div>

      <div className="card-surface p-6 space-y-3">
        <h3 className="text-lg font-semibold">方案</h3>
        <div className="grid md:grid-cols-2 gap-3">
          {plans
            .filter((plan) => !plan.is_trial)
            .map((plan) => (
            <div key={plan.id} className="rounded-xl border border-[var(--line)] bg-[#fbfefe] p-4 space-y-2">
              <p className="font-semibold">{plan.name}</p>
              <p className="text-sm text-slate-600">{plan.description || "-"}</p>
              <p className="text-sm text-slate-700">
                價格：{(plan.price_cents / 100).toLocaleString()} {plan.currency} / {plan.duration_days} 天
              </p>
              <button className="brand-btn px-4 py-2" onClick={() => createCheckout(plan.code)}>
                建立付款
              </button>
            </div>
            ))}
        </div>

        {checkout && (
          <div className="rounded-xl border border-[#c7ebe8] bg-[#f3fbfb] p-4 space-y-2 text-sm">
            <p>交易編號：{checkout.txn_id}</p>
            <p>
              金額：{(checkout.amount_cents / 100).toLocaleString()} {checkout.currency}
            </p>
            <button className="brand-btn-secondary px-4 py-2" onClick={markPaid}>
              模擬付款成功（Webhook）
            </button>
          </div>
        )}

        {status && <p className="text-sm text-slate-700">{status}</p>}
      </div>
    </section>
  );
}
