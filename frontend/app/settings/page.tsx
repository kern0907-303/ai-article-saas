"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { ImageSettings, ModelCatalogItem } from "@/lib/types";

export default function SettingsPage() {
  const [form, setForm] = useState({
    openai_api_key: "",
    website_api_key: "",
    social_api_key: "",
    article_model: "gpt-4.1-mini",
    prompt_model: "gpt-4.1-mini",
    image_model: "gpt-image-1",
    website_endpoint: "",
    social_endpoint: "",
    notes: "",
  });
  const [imageSettings, setImageSettings] = useState<ImageSettings | null>(null);
  const [modelCatalog, setModelCatalog] = useState<ModelCatalogItem[]>([]);
  const [status, setStatus] = useState("");

  useEffect(() => {
    Promise.all([api.getSettings(), api.getImageSettings(), api.getModelCatalog()])
      .then(([settingsData, imageData, modelData]) => {
        if (settingsData) {
          setForm({
            openai_api_key: settingsData.openai_api_key || "",
            website_api_key: settingsData.website_api_key || "",
            social_api_key: settingsData.social_api_key || "",
            article_model: settingsData.article_model || "gpt-4.1-mini",
            prompt_model: settingsData.prompt_model || "gpt-4.1-mini",
            image_model: settingsData.image_model || "gpt-image-1",
            website_endpoint: settingsData.website_endpoint || "",
            social_endpoint: settingsData.social_endpoint || "",
            notes: settingsData.notes || "",
          });
        }
        setImageSettings(imageData);
        setModelCatalog(modelData.models || []);
      })
      .catch((err: Error) => setStatus(`讀取失敗：${err.message}`));
  }, []);

  const textModels = useMemo(() => modelCatalog.filter((m) => m.category === "text"), [modelCatalog]);
  const imageModels = useMemo(() => modelCatalog.filter((m) => m.category === "image"), [modelCatalog]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("儲存中...");
    try {
      await api.saveSettings(form);
      if (imageSettings) {
        await api.saveImageSettings(imageSettings);
      }
      setStatus("儲存成功，現在可前往「文章創作與發布」測試。 ");
    } catch (err) {
      setStatus(`儲存失敗：${(err as Error).message}`);
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
        <Input
          label="AI 服務 API Key (如 OpenAI / Anthropic)"
          value={form.openai_api_key}
          onChange={(v) => setForm({ ...form, openai_api_key: v })}
          hint="必填。未填此欄會無法生成文章與提示詞。"
          linkText="👉 一步一步看 AI Key 申請與貼上方式"
          linkHref="/help/api-setup#ai-key"
          placeholder="sk-..."
        />

        <div className="rounded-xl border border-[#c7ebe8] bg-[#f3fbfb] p-4 space-y-3">
          <h3 className="font-semibold text-[#0f766e]">AI 模型選擇（含成本層級）</h3>
          <div className="grid md:grid-cols-3 gap-3">
            <Select
              label="文章生成模型"
              value={form.article_model}
              options={textModels}
              onChange={(v) => setForm({ ...form, article_model: v })}
            />
            <Select
              label="提示詞擴寫模型"
              value={form.prompt_model}
              options={textModels}
              onChange={(v) => setForm({ ...form, prompt_model: v })}
            />
            <Select
              label="圖片模型"
              value={form.image_model}
              options={imageModels}
              onChange={(v) => setForm({ ...form, image_model: v })}
            />
          </div>
          <p className="text-xs text-slate-600">成本層級：low（低）/ medium（中）/ high（高）</p>
        </div>

        <div className="rounded-xl border border-[#c7ebe8] bg-[#f3fbfb] p-4 space-y-3">
          <h3 className="font-semibold text-[#0f766e]">圖片生成後台設定（含 nano banana 中文優先）</h3>
          {imageSettings && (
            <>
              <label className="block text-sm font-medium text-slate-700">
                Provider 模式
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 p-2"
                  value={imageSettings.image_provider_mode}
                  onChange={(e) =>
                    setImageSettings({ ...imageSettings, image_provider_mode: e.target.value as ImageSettings["image_provider_mode"] })
                  }
                >
                  <option value="auto">auto（建議）</option>
                  <option value="nano_banana">nano_banana</option>
                  <option value="openai">openai</option>
                  <option value="stability">stability</option>
                </select>
              </label>

              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={imageSettings.force_nano_banana_for_zh_text}
                  onChange={(e) =>
                    setImageSettings({ ...imageSettings, force_nano_banana_for_zh_text: e.target.checked })
                  }
                />
                中文文字需求時強制走 nano banana（建議開啟）
              </label>

              <div className="grid md:grid-cols-2 gap-3">
                <InputSimple
                  label="每篇預設圖片數"
                  value={String(imageSettings.images_per_article)}
                  onChange={(v) => setImageSettings({ ...imageSettings, images_per_article: Number(v) || 1 })}
                />
                <InputSimple
                  label="預設尺寸"
                  value={imageSettings.default_size}
                  onChange={(v) => setImageSettings({ ...imageSettings, default_size: v })}
                />
              </div>

              <InputSimple
                label="中文文字偵測關鍵字（逗號分隔）"
                value={imageSettings.zh_text_detection_keywords}
                onChange={(v) => setImageSettings({ ...imageSettings, zh_text_detection_keywords: v })}
              />
            </>
          )}
        </div>

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
