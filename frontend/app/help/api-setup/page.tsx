import Link from "next/link";

const checklist = [
  "已填 AI 服務 API Key",
  "已儲存設定且顯示成功",
  "已在文章頁點過「生成精準提示詞」測試",
  "若要自動發布，已填網站/社群 API Key 與 Endpoint",
];

export default function ApiSetupHelpPage() {
  return (
    <section className="max-w-5xl space-y-6">
      <header className="card-surface p-6 space-y-3">
        <span className="brand-pill">操作教學</span>
        <h2 className="text-2xl font-bold">API Key 與 Endpoint 逐步設定指南</h2>
        <p className="text-slate-700">這份教學不是概念說明，而是「照著做就能成功」的流程。新手建議從步驟 1 開始。</p>
        <div className="flex gap-3 flex-wrap text-sm">
          <Link href="/settings" className="brand-btn-secondary px-3 py-1.5">
            返回系統設定
          </Link>
          <a href="#quick-check" className="brand-link">
            跳到完成檢查清單
          </a>
        </div>
      </header>

      <article id="ai-key" className="card-surface p-6 space-y-3">
        <h3 className="text-lg font-semibold">步驟 1：先完成 AI 服務 API Key（必要）</h3>
        <ol className="list-decimal pl-5 space-y-2 text-sm text-slate-700">
          <li>到官方平台建立帳號並完成付款/用量設定。</li>
          <li>進入 API Keys 頁面建立新金鑰。</li>
          <li>回到「系統設定」，貼到「AI 服務 API Key」欄位。</li>
          <li>按「儲存設定」。</li>
          <li>到文章頁按一次「生成精準提示詞」確認可用。</li>
        </ol>
        <div className="text-sm text-slate-600 space-y-1">
          <p>官方文件：</p>
          <a href="https://platform.openai.com/docs/overview" target="_blank" rel="noreferrer" className="block brand-link">
            OpenAI Platform Docs
          </a>
          <a href="https://docs.anthropic.com/" target="_blank" rel="noreferrer" className="block brand-link">
            Anthropic Docs
          </a>
        </div>
      </article>

      <div className="grid md:grid-cols-2 gap-4">
        <article id="website" className="card-surface p-6 space-y-3">
          <h3 className="text-lg font-semibold">步驟 2A：設定個人網頁發布</h3>
          <ol className="list-decimal pl-5 space-y-2 text-sm text-slate-700">
            <li>在你網站後端建立「可發布文章」的 API 金鑰。</li>
            <li>確認後端有提供 HTTP API 接收文章。</li>
            <li>把 API Key 貼到「個人網頁 API Key」。</li>
            <li>把 API URL 貼到「個人網頁 Endpoint」。</li>
          </ol>
        </article>

        <article id="social" className="card-surface p-6 space-y-3">
          <h3 className="text-lg font-semibold">步驟 2B：設定社交平台發布</h3>
          <ol className="list-decimal pl-5 space-y-2 text-sm text-slate-700">
            <li>到社群平台開發者後台建立應用。</li>
            <li>取得 API 金鑰/Token（依平台規範）。</li>
            <li>把金鑰貼到「社交平台 API Key」。</li>
            <li>把 API URL 貼到「社交平台 Endpoint」。</li>
          </ol>
        </article>
      </div>

      <article id="endpoint-example" className="card-surface p-6 space-y-3">
        <h3 className="text-lg font-semibold">步驟 3：Endpoint 格式與驗證方式</h3>
        <div className="text-sm text-slate-700 space-y-2">
          <p>個人網頁 Endpoint 範例：<code>https://api.yoursite.com/publish</code></p>
          <p>社交平台 Endpoint 範例：<code>https://api.social.com/post</code></p>
          <p>建議：只用 HTTPS、限制來源 IP、對每次請求做授權檢查與日誌記錄。</p>
        </div>
      </article>

      <article id="quick-check" className="card-surface p-6 space-y-3">
        <h3 className="text-lg font-semibold">完成檢查清單（照此驗收）</h3>
        <ul className="space-y-2 text-sm text-slate-700">
          {checklist.map((item) => (
            <li key={item} className="flex items-start gap-2">
              <span className="mt-[2px] text-[#0a9e99]">✓</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </article>

      <article id="best-practice" className="card-surface p-6 space-y-3">
        <h3 className="text-lg font-semibold">常見錯誤與快速排除</h3>
        <div className="grid md:grid-cols-2 gap-3 text-sm text-slate-700">
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="font-semibold">錯誤：提示詞擴寫失敗（未設定 AI Key）</p>
            <p className="mt-1">回到系統設定填入 AI Key，按儲存後重試。</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="font-semibold">錯誤：發布失敗</p>
            <p className="mt-1">檢查 Endpoint 是否可連線、Token 是否過期、權限是否足夠。</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="font-semibold">安全建議</p>
            <p className="mt-1">API Key 外洩時立刻輪替，正式與測試環境分開使用。</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="font-semibold">團隊交接</p>
            <p className="mt-1">把金鑰用途與更新日期寫在「備註」欄，降低維運風險。</p>
          </div>
        </div>
      </article>
    </section>
  );
}
