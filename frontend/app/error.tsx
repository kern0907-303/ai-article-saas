"use client";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <section className="card-surface max-w-xl w-full p-6 space-y-4">
        <span className="brand-pill">系統保護機制</span>
        <h2 className="text-2xl font-bold text-slate-800">頁面暫時發生錯誤</h2>
        <p className="text-slate-700">
          我們已攔截錯誤，系統仍可運作。請先點「重新載入此頁」，若仍發生請回報錯誤訊息。
        </p>
        <pre className="rounded-lg bg-slate-50 border border-slate-200 p-3 text-xs text-slate-600 overflow-auto">
          {error?.message || "未知錯誤"}
        </pre>
        <button className="brand-btn px-4 py-2" onClick={reset}>
          重新載入此頁
        </button>
      </section>
    </main>
  );
}
