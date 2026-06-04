"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { GoogleSheetDestination, ModelCatalogItem, Settings } from "@/lib/types";

const PROVIDER_DEFAULTS: Record<Settings["ai_provider"], { article: string; prompt: string; keyHint: string; keyPlaceholder: string }> = {
  openai: {
    article: "gpt-5.4-mini",
    prompt: "gpt-5.4-mini",
    keyHint: "使用 OpenAI 平台發出的 API Key，通常以 sk- 開頭。",
    keyPlaceholder: "sk-...",
  },
  anthropic: {
    article: "claude-sonnet-4-6",
    prompt: "claude-haiku-4-5",
    keyHint: "使用 Anthropic Console 發出的 API Key。",
    keyPlaceholder: "sk-ant-...",
  },
  gemini: {
    article: "gemini-3.5-flash",
    prompt: "gemini-3.1-flash-lite",
    keyHint: "使用 Google AI Studio 或 Gemini API 發出的 API Key。",
    keyPlaceholder: "AIza...",
  },
  github: {
    article: "openai/gpt-5.4",
    prompt: "openai/gpt-5.4-mini",
    keyHint: "使用 GitHub token，並確認 fine-grained PAT 具備 models: read 權限。",
    keyPlaceholder: "ghp_... / github_pat_...",
  },
};

const FALLBACK_TEXT_MODELS: Record<Settings["ai_provider"], ModelCatalogItem[]> = {
  openai: [
    { key: "gpt-5.4-mini", provider: "openai", category: "text", label: "GPT-5.4 Mini", description: "", cost_tier: "low" },
    { key: "gpt-5.4", provider: "openai", category: "text", label: "GPT-5.4", description: "", cost_tier: "high" },
    { key: "gpt-5.5", provider: "openai", category: "text", label: "GPT-5.5", description: "", cost_tier: "high" },
  ],
  anthropic: [
    { key: "claude-haiku-4-5", provider: "anthropic", category: "text", label: "Claude Haiku 4.5", description: "", cost_tier: "low" },
    { key: "claude-sonnet-4-6", provider: "anthropic", category: "text", label: "Claude Sonnet 4.6", description: "", cost_tier: "medium" },
    { key: "claude-opus-4-8", provider: "anthropic", category: "text", label: "Claude Opus 4.8", description: "", cost_tier: "high" },
  ],
  gemini: [
    { key: "gemini-3.1-flash-lite", provider: "gemini", category: "text", label: "Gemini 3.1 Flash-Lite", description: "", cost_tier: "low" },
    { key: "gemini-3.5-flash", provider: "gemini", category: "text", label: "Gemini 3.5 Flash", description: "", cost_tier: "low" },
    { key: "gemini-3.1-pro", provider: "gemini", category: "text", label: "Gemini 3.1 Pro", description: "", cost_tier: "high" },
  ],
  github: [
    { key: "openai/gpt-5.4-mini", provider: "github", category: "text", label: "GitHub Models: GPT-5.4 Mini", description: "", cost_tier: "low" },
    { key: "openai/gpt-5.4", provider: "github", category: "text", label: "GitHub Models: GPT-5.4", description: "", cost_tier: "high" },
  ],
};

const FALLBACK_IMAGE_MODELS: ModelCatalogItem[] = [
  { key: "gpt-image-2", provider: "openai", category: "image", label: "GPT Image 2", description: "", cost_tier: "medium" },
  { key: "nano-banana-pro", provider: "nano_banana", category: "image", label: "Nano Banana Pro", description: "", cost_tier: "medium" },
];

function getActiveProviderKey(form: {
  ai_provider: Settings["ai_provider"];
  openai_api_key: string;
  anthropic_api_key: string;
  gemini_api_key: string;
  github_api_key: string;
}): string {
  if (form.ai_provider === "openai") return form.openai_api_key.trim();
  if (form.ai_provider === "anthropic") return form.anthropic_api_key.trim();
  if (form.ai_provider === "gemini") return form.gemini_api_key.trim();
  return form.github_api_key.trim();
}

function validateProviderKey(provider: Settings["ai_provider"], apiKey: string): string | null {
  if (!apiKey) {
    return "請先填入目前所選供應商的 API Key。";
  }

  if (provider === "openai" && !apiKey.startsWith("sk-")) {
    return "OpenAI API Key 格式看起來不正確，通常會以 sk- 開頭。";
  }
  if (provider === "anthropic" && !apiKey.startsWith("sk-ant-")) {
    return "Anthropic API Key 格式看起來不正確，通常會以 sk-ant- 開頭。";
  }
  if (provider === "gemini" && !apiKey.startsWith("AIza")) {
    return "Gemini API Key 格式看起來不正確，通常會以 AIza 開頭。";
  }
  if (provider === "github" && !(apiKey.startsWith("ghp_") || apiKey.startsWith("github_pat_"))) {
    return "GitHub Models token 建議使用 ghp_ 或 github_pat_ 開頭的 GitHub token。";
  }

  return null;
}

export default function SettingsPage() {
  const [form, setForm] = useState({
    ai_provider: "openai" as Settings["ai_provider"],
    openai_api_key: "",
    anthropic_api_key: "",
    gemini_api_key: "",
    github_api_key: "",
    website_api_key: "",
    social_api_key: "",
    article_model: "gpt-5.4-mini",
    prompt_model: "gpt-5.4-mini",
    image_model: "gpt-image-2",
    website_endpoint: "",
    social_endpoint: "",
    notes: "",
  });
  const [modelCatalog, setModelCatalog] = useState<ModelCatalogItem[]>([]);
  const [sheetDestinations, setSheetDestinations] = useState<GoogleSheetDestination[]>([]);
  const [sheetForm, setSheetForm] = useState({
    id: null as number | null,
    label: "",
    spreadsheet_id: "",
    sheet_name: "文章準備",
    service_account_json: "",
    is_default: false,
  });
  const [status, setStatus] = useState("");
  const [sheetStatus, setSheetStatus] = useState("");
  const [showAdvancedPublish, setShowAdvancedPublish] = useState(false);

  useEffect(() => {
    let mounted = true;

    api
      .getSettings()
      .then((settingsData) => {
        if (!mounted || !settingsData) return;
        setForm({
          ai_provider: settingsData.ai_provider || "openai",
          openai_api_key: settingsData.openai_api_key || "",
          anthropic_api_key: settingsData.anthropic_api_key || "",
          gemini_api_key: settingsData.gemini_api_key || "",
          github_api_key: settingsData.github_api_key || "",
          website_api_key: settingsData.website_api_key || "",
          social_api_key: settingsData.social_api_key || "",
          article_model: settingsData.article_model || "gpt-5.4-mini",
          prompt_model: settingsData.prompt_model || "gpt-5.4-mini",
          image_model: settingsData.image_model || "gpt-image-2",
          website_endpoint: settingsData.website_endpoint || "",
          social_endpoint: settingsData.social_endpoint || "",
          notes: settingsData.notes || "",
        });
      })
      .catch((err: Error) => {
        if (!mounted) return;
        setStatus(`部分設定讀取失敗：${err.message}`);
      });

    api
      .getModelCatalog()
      .then((modelData) => {
        if (!mounted) return;
        setModelCatalog(modelData.models || []);
      })
      .catch((err: Error) => {
        if (!mounted) return;
        setStatus((prev) => prev || `模型清單讀取失敗，已先使用預設值：${err.message}`);
      });

    api
      .listGoogleSheetDestinations()
      .then((items) => {
        if (!mounted) return;
        setSheetDestinations(items);
      })
      .catch((err: Error) => {
        if (!mounted) return;
        setSheetStatus(`Google Sheets 目的地讀取失敗：${err.message}`);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const textModels = useMemo(
    () => modelCatalog.filter((m) => m.category === "text" && m.provider === form.ai_provider),
    [form.ai_provider, modelCatalog],
  );
  const imageModels = useMemo(() => modelCatalog.filter((m) => m.category === "image"), [modelCatalog]);
  const effectiveTextModels = textModels.length > 0 ? textModels : FALLBACK_TEXT_MODELS[form.ai_provider];
  const effectiveImageModels = imageModels.length > 0 ? imageModels : FALLBACK_IMAGE_MODELS;
  const providerConfig = PROVIDER_DEFAULTS[form.ai_provider];

  useEffect(() => {
    if (effectiveTextModels.length === 0) return;

    setForm((prev) => {
      const next = { ...prev };
      if (!effectiveTextModels.some((model) => model.key === prev.article_model)) {
        next.article_model = PROVIDER_DEFAULTS[prev.ai_provider].article;
      }
      if (!effectiveTextModels.some((model) => model.key === prev.prompt_model)) {
        next.prompt_model = PROVIDER_DEFAULTS[prev.ai_provider].prompt;
      }
      return next;
    });
  }, [effectiveTextModels]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const activeProviderKey = getActiveProviderKey(form);
    const keyError = validateProviderKey(form.ai_provider, activeProviderKey);
    if (keyError) {
      setStatus(keyError);
      return;
    }

    setStatus("儲存中...");
    try {
      await api.saveSettings(form);
      setStatus("儲存成功，現在可前往「文章創作與發布」測試。 ");
    } catch (err) {
      setStatus(`儲存失敗：${(err as Error).message}`);
    }
  };

  const resetSheetForm = () => {
    setSheetForm({
      id: null,
      label: "",
      spreadsheet_id: "",
      sheet_name: "文章準備",
      service_account_json: "",
      is_default: false,
    });
  };

  const refreshSheetDestinations = async () => {
    const items = await api.listGoogleSheetDestinations();
    setSheetDestinations(items);
  };

  const saveSheetDestination = async () => {
    if (!sheetForm.label.trim() || !sheetForm.spreadsheet_id.trim() || !sheetForm.sheet_name.trim()) {
      setSheetStatus("請填入目的地名稱、Spreadsheet ID 與工作表名稱");
      return;
    }
    if (!sheetForm.id && !sheetForm.service_account_json.trim()) {
      setSheetStatus("新增目的地時必須貼上 Service Account JSON");
      return;
    }

    setSheetStatus("Google Sheets 目的地儲存中...");
    try {
      const payload = {
        label: sheetForm.label.trim(),
        spreadsheet_id: sheetForm.spreadsheet_id.trim(),
        sheet_name: sheetForm.sheet_name.trim(),
        service_account_json: sheetForm.service_account_json.trim() || undefined,
        is_default: sheetForm.is_default,
      };
      if (sheetForm.id) {
        await api.updateGoogleSheetDestination(sheetForm.id, payload);
      } else {
        await api.createGoogleSheetDestination({ ...payload, service_account_json: sheetForm.service_account_json.trim() });
      }
      await refreshSheetDestinations();
      resetSheetForm();
      setSheetStatus("Google Sheets 目的地已儲存");
    } catch (err) {
      setSheetStatus(`Google Sheets 目的地儲存失敗：${(err as Error).message}`);
    }
  };

  const editSheetDestination = (destination: GoogleSheetDestination) => {
    setSheetForm({
      id: destination.id,
      label: destination.label,
      spreadsheet_id: destination.spreadsheet_id,
      sheet_name: destination.sheet_name,
      service_account_json: "",
      is_default: destination.is_default,
    });
    setSheetStatus("正在編輯目的地。若不更換 Service Account，JSON 欄位可留空。");
  };

  const deleteSheetDestination = async (destination: GoogleSheetDestination) => {
    const ok = window.confirm(`確定要刪除「${destination.label}」嗎？`);
    if (!ok) return;
    setSheetStatus("刪除 Google Sheets 目的地中...");
    try {
      await api.deleteGoogleSheetDestination(destination.id);
      await refreshSheetDestinations();
      if (sheetForm.id === destination.id) resetSheetForm();
      setSheetStatus("Google Sheets 目的地已刪除");
    } catch (err) {
      setSheetStatus(`刪除失敗：${(err as Error).message}`);
    }
  };

  return (
    <section className="max-w-4xl space-y-5">
      <div className="card-surface p-6 space-y-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="text-2xl font-bold">系統設定</h2>
          <span className="brand-pill">降低設定門檻</span>
        </div>
        <p className="text-slate-700">請先完成下面 3 步，整個平台就能正常生成、配圖與發布。</p>
        <p className="text-sm text-slate-500">
          不確定怎麼做？
          <Link href="/help/api-setup" className="ml-1 brand-link">
            打開逐步操作教學（含官方文件與排錯）
          </Link>
        </p>
      </div>

      <form onSubmit={onSubmit} className="card-surface p-6 space-y-4">
        <label className="block text-sm font-medium text-slate-700">
          文字模型供應商
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            value={form.ai_provider}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                ai_provider: e.target.value as Settings["ai_provider"],
                article_model: PROVIDER_DEFAULTS[e.target.value as Settings["ai_provider"]].article,
                prompt_model: PROVIDER_DEFAULTS[e.target.value as Settings["ai_provider"]].prompt,
              }))
            }
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="gemini">Gemini</option>
            <option value="github">GitHub Models</option>
          </select>
          <p className="mt-1 text-xs text-slate-500">文章生成與提示詞擴寫會依這裡選的供應商切換。</p>
        </label>

        <Input
          label="OpenAI API Key"
          value={form.openai_api_key}
          onChange={(v) => setForm({ ...form, openai_api_key: v })}
          hint={form.ai_provider === "openai" ? providerConfig.keyHint : "選填。切換到 OpenAI 時會使用這組金鑰。"}
          linkText="👉 一步一步看 AI Key 申請與貼上方式"
          linkHref="/help/api-setup#ai-key"
          placeholder={form.ai_provider === "openai" ? providerConfig.keyPlaceholder : "sk-..."}
        />

        <Input
          label="Anthropic API Key"
          value={form.anthropic_api_key}
          onChange={(v) => setForm({ ...form, anthropic_api_key: v })}
          hint={form.ai_provider === "anthropic" ? providerConfig.keyHint : "選填。切換到 Anthropic 時會使用這組金鑰。"}
          linkText="👉 前往 Anthropic Console 建立 API Key"
          linkHref="/help/api-setup#ai-key"
          placeholder={form.ai_provider === "anthropic" ? providerConfig.keyPlaceholder : "sk-ant-..."}
        />

        <Input
          label="Gemini API Key"
          value={form.gemini_api_key}
          onChange={(v) => setForm({ ...form, gemini_api_key: v })}
          hint={form.ai_provider === "gemini" ? providerConfig.keyHint : "選填。切換到 Gemini 時會使用這組金鑰。"}
          linkText="👉 前往 Google AI Studio 建立 API Key"
          linkHref="/help/api-setup#ai-key"
          placeholder={form.ai_provider === "gemini" ? providerConfig.keyPlaceholder : "AIza..."}
        />

        <Input
          label="GitHub Models Token"
          value={form.github_api_key}
          onChange={(v) => setForm({ ...form, github_api_key: v })}
          hint={form.ai_provider === "github" ? providerConfig.keyHint : "選填。切換到 GitHub Models 時會使用這組 token。"}
          linkText="👉 查看 GitHub Models token 與權限說明"
          linkHref="/help/api-setup#ai-key"
          placeholder={form.ai_provider === "github" ? providerConfig.keyPlaceholder : "ghp_... / github_pat_..."}
        />

        <div className="rounded-xl border border-[var(--line)] bg-[linear-gradient(135deg,#fff6da,#ffe0ab)] p-4 space-y-3">
          <h3 className="font-semibold text-[var(--text)]">核心模型設定</h3>
          <p className="text-xs text-slate-600">目前供應商：{form.ai_provider}</p>
          <div className="grid md:grid-cols-3 gap-3">
            <Select
              label="文章生成模型"
              value={form.article_model}
              options={effectiveTextModels}
              onChange={(v) => setForm({ ...form, article_model: v })}
            />
            <Select
              label="提示詞擴寫模型"
              value={form.prompt_model}
              options={effectiveTextModels}
              onChange={(v) => setForm({ ...form, prompt_model: v })}
            />
            <Select
              label="圖片模型"
              value={form.image_model}
              options={effectiveImageModels}
              onChange={(v) => setForm({ ...form, image_model: v })}
            />
          </div>
          <p className="text-xs text-slate-600">成本層級：low（低）/ medium（中）/ high（高）</p>
          <p className="text-xs text-slate-500">圖片生成已改成自動最佳化，不再需要另外設定一堆圖片後台參數。</p>
          {form.ai_provider === "github" && (
            <div className="rounded-lg border border-dashed border-[#efb24e] bg-white/70 p-3 space-y-3">
              <p className="text-xs text-slate-600">
                GitHub Models 可直接選常用模型，也可手動輸入 model ID。若 GitHub 更新模型清單，你可以直接覆蓋下面欄位。
              </p>
              <div className="grid md:grid-cols-2 gap-3">
                <InputSimple
                  label="GitHub 文章模型 ID"
                  value={form.article_model}
                  onChange={(v) => setForm({ ...form, article_model: v })}
                />
                <InputSimple
                  label="GitHub 提示詞模型 ID"
                  value={form.prompt_model}
                  onChange={(v) => setForm({ ...form, prompt_model: v })}
                />
              </div>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-[var(--line)] bg-[rgba(255,248,231,0.82)] p-4 space-y-4">
          <div>
            <h3 className="font-semibold text-[var(--text)]">Google Sheets 上傳目的地</h3>
            <p className="mt-1 text-xs text-slate-600">可建立多個 Spreadsheet ID，對應不同客戶、品牌帳號或內容準備頁。</p>
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            <InputSimple label="目的地名稱" value={sheetForm.label} onChange={(v) => setSheetForm({ ...sheetForm, label: v })} />
            <InputSimple
              label="Spreadsheet ID"
              value={sheetForm.spreadsheet_id}
              onChange={(v) => setSheetForm({ ...sheetForm, spreadsheet_id: v })}
            />
            <InputSimple label="工作表名稱" value={sheetForm.sheet_name} onChange={(v) => setSheetForm({ ...sheetForm, sheet_name: v })} />
            <label className="flex items-center gap-2 pt-6 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={sheetForm.is_default}
                onChange={(e) => setSheetForm({ ...sheetForm, is_default: e.target.checked })}
              />
              設為預設上傳目的地
            </label>
          </div>

          <label className="block text-sm font-medium text-slate-700">
            Service Account JSON
            <textarea
              className="mt-1 w-full rounded-lg border border-slate-300 p-2 font-mono text-xs"
              rows={5}
              value={sheetForm.service_account_json}
              onChange={(e) => setSheetForm({ ...sheetForm, service_account_json: e.target.value })}
              placeholder={sheetForm.id ? "不更換 Service Account 時可留空" : "{\"client_email\":\"...\",\"private_key\":\"...\"}"}
            />
          </label>

          <div className="flex gap-2 flex-wrap">
            <button type="button" className="brand-btn-secondary px-4 py-2" onClick={saveSheetDestination}>
              {sheetForm.id ? "更新目的地" : "新增目的地"}
            </button>
            {sheetForm.id && (
              <button type="button" className="rounded-lg border border-[var(--line)] bg-white/75 px-4 py-2 text-sm" onClick={resetSheetForm}>
                取消編輯
              </button>
            )}
          </div>

          {sheetDestinations.length > 0 && (
            <div className="space-y-2">
              {sheetDestinations.map((destination) => (
                <div key={destination.id} className="rounded-xl border border-[var(--line)] bg-white/80 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-800">
                        {destination.label} {destination.is_default ? "（預設）" : ""}
                      </p>
                      <p className="mt-1 break-all text-xs text-slate-600">Spreadsheet ID：{destination.spreadsheet_id}</p>
                      <p className="text-xs text-slate-600">
                        工作表：{destination.sheet_name} / Service Account：{destination.service_account_email}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button type="button" className="brand-btn-secondary px-3 py-2 text-sm" onClick={() => editSheetDestination(destination)}>
                        編輯
                      </button>
                      <button type="button" className="brand-btn-danger px-3 py-2 text-sm" onClick={() => deleteSheetDestination(destination)}>
                        刪除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {sheetStatus && <p className="text-sm text-slate-600">{sheetStatus}</p>}
        </div>

        <div className="rounded-xl border border-[var(--line)] bg-[rgba(255,248,231,0.82)] p-4 space-y-3">
          <button
            type="button"
            className="text-sm font-semibold text-slate-700"
            onClick={() => setShowAdvancedPublish((prev) => !prev)}
          >
            {showAdvancedPublish ? "收合進階發布設定" : "展開進階發布設定"}
          </button>
          <p className="text-xs text-slate-500">只有要發布到網站或社群時，才需要填下面欄位。</p>

          {showAdvancedPublish && (
            <div className="space-y-4">
              <Input
                label="個人網頁 API Key"
                value={form.website_api_key}
                onChange={(v) => setForm({ ...form, website_api_key: v })}
                hint="選填（若需發布到網站則必填）。"
                linkText="👉 網站 API Key 取得流程與權限設定"
                linkHref="/help/api-setup#website"
                placeholder="your-website-key"
              />

              <Input
                label="社交平台 API Key"
                value={form.social_api_key}
                onChange={(v) => setForm({ ...form, social_api_key: v })}
                hint="選填（若需發布到社群則必填）。"
                linkText="👉 社群平台授權與 API Key 設定"
                linkHref="/help/api-setup#social"
                placeholder="your-social-key"
              />

              <Input
                label="個人網頁 Endpoint"
                value={form.website_endpoint}
                onChange={(v) => setForm({ ...form, website_endpoint: v })}
                hint="你的網站接收文章發布的 API 網址。"
                linkText="👉 Endpoint 格式範例與測試方式"
                linkHref="/help/api-setup#endpoint-example"
                placeholder="https://api.yoursite.com/publish"
              />

              <Input
                label="社交平台 Endpoint"
                value={form.social_endpoint}
                onChange={(v) => setForm({ ...form, social_endpoint: v })}
                hint="你的社群代理服務接收文章的 API 網址。"
                linkText="👉 Endpoint 格式範例與測試方式"
                linkHref="/help/api-setup#endpoint-example"
                placeholder="https://api.social.com/post"
              />

              <label className="block text-sm font-medium text-slate-700">
                備註
                <textarea
                  className="mt-1 w-full rounded-lg border border-slate-300 p-2"
                  rows={4}
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="例如：這組金鑰是測試環境，僅供內部驗證。"
                />
              </label>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button type="submit" className="brand-btn px-4 py-2">
            儲存設定
          </button>
          {status && <p className="text-sm text-slate-600">{status}</p>}
        </div>
      </form>
    </section>
  );
}

function Input({
  label,
  value,
  onChange,
  hint,
  linkText,
  linkHref,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  hint: string;
  linkText: string;
  linkHref: string;
  placeholder: string;
}) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input
        className="mt-1 w-full rounded-lg border border-slate-300 p-2"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
      <Link href={linkHref} className="text-xs brand-link">
        {linkText}
      </Link>
    </label>
  );
}

function InputSimple({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input className="mt-1 w-full rounded-lg border border-slate-300 p-2" value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: ModelCatalogItem[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <select className="mt-1 w-full rounded-lg border border-slate-300 p-2" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((item) => (
          <option key={item.key} value={item.key}>
            {item.label} ({item.cost_tier})
          </option>
        ))}
      </select>
    </label>
  );
}
