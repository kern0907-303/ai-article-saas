"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { api } from "@/lib/api";
import {
  Article,
  ArticleImage,
  Entitlements,
  GoogleSheetDestination,
  ImageSizePreset,
  ImageStylePreset,
  KnowledgeFile,
} from "@/lib/types";

const PROMPT_TEMPLATES = [
  {
    key: "blogger",
    label: "部落客深度分享風格",
    value:
      "你是一位有個人特色的專業部落客。請用自然、有溫度且容易閱讀的語氣寫作，先用生活化情境破題，再逐步展開重點。文章需兼具故事感與實用性，包含：吸引人的標題、開場鉤子、3-5 個核心觀點、可立即行動的建議、結尾互動提問。請避免空泛口號，讓讀者看完就想收藏與分享。",
  },
  {
    key: "expert",
    label: "專家觀點權威解析",
    value:
      "你是該領域的資深專家與顧問。請以嚴謹、可信、可驗證的方式分析主題，先定義問題，再拆解成原理、方法、案例與風險。內容需包含：關鍵術語解釋、常見誤區、決策建議、評估指標與落地步驟。語氣專業但不艱澀，避免誇大與無根據結論，讓讀者能用於實務判斷。",
  },
  {
    key: "emotion",
    label: "情感抒發共鳴文章",
    value:
      "請用細膩真誠的筆觸撰寫一篇情感抒發文章，重點是「真實感」與「共鳴感」。結構建議：一段具體情境開場、內在情緒拉扯、轉折反思、溫柔收束。避免過度灑狗血或說教，改用可感知的細節與節制語言表達，讓讀者覺得被理解、被陪伴。",
  },
  {
    key: "knowledge",
    label: "知識與認知升級分享",
    value:
      "請以「認知升級 + 知識轉譯」方式寫作，幫助一般讀者快速理解複雜主題。先講清楚為何重要，再用比喻、框架與實例拆解，最後整理成可執行清單。內容需包含：核心概念、常見迷思、判斷框架、實戰情境、下一步行動。語氣清楚、有邏輯、不賣弄術語，重點是讓讀者看完能真正學會並應用。",
  },
];

export default function ArticlesPage() {
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [images, setImages] = useState<ArticleImage[]>([]);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [stylePresets, setStylePresets] = useState<ImageStylePreset[]>([]);
  const [sizePresets, setSizePresets] = useState<ImageSizePreset[]>([]);
  const [sheetDestinations, setSheetDestinations] = useState<GoogleSheetDestination[]>([]);
  const [selectedImageStyle, setSelectedImageStyle] = useState("blog_cover");
  const [selectedImageSize, setSelectedImageSize] = useState("instagram_square");
  const [selectedSheetDestinationId, setSelectedSheetDestinationId] = useState<number | null>(null);
  const [needTextOverlay, setNeedTextOverlay] = useState(true);
  const [imageTextLanguage, setImageTextLanguage] = useState("zh-Hant");
  const [imageTextContent, setImageTextContent] = useState("");

  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [topic, setTopic] = useState("");
  const [outline, setOutline] = useState("");
  const [prompt, setPrompt] = useState("");
  const [promptRequirement, setPromptRequirement] = useState("");
  const [templateKey, setTemplateKey] = useState("");
  const [content, setContent] = useState("");
  const [currentArticleId, setCurrentArticleId] = useState<number | null>(null);
  const [status, setStatus] = useState("");
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const [loadingArticle, setLoadingArticle] = useState(false);
  const [loadingImages, setLoadingImages] = useState(false);
  const [savingContent, setSavingContent] = useState(false);
  const [exportingSheet, setExportingSheet] = useState(false);
  const [publishingChannel, setPublishingChannel] = useState<"website" | "social" | null>(null);
  const [pollingArticleId, setPollingArticleId] = useState<number | null>(null);
  const [pollingImageArticleId, setPollingImageArticleId] = useState<number | null>(null);

  const currentArticle = useMemo(
    () => articles.find((item) => item.id === currentArticleId) || null,
    [articles, currentArticleId],
  );

  const load = async () => {
    const [presets, sizes, sheets, entitlementData] = await Promise.all([
      api.getImageStylePresets(),
      api.getImageSizePresets(),
      api.listGoogleSheetDestinations(),
      api.getEntitlements(),
    ]);
    setStylePresets(presets);
    setSizePresets(sizes);
    setSheetDestinations(sheets);
    setSelectedSheetDestinationId((prev) => prev || sheets.find((item) => item.is_default)?.id || sheets[0]?.id || null);
    setEntitlements(entitlementData);

    if (!entitlementData.is_active) {
      setFiles([]);
      setArticles([]);
      setImages([]);
      setCurrentArticleId(null);
      return;
    }

    const [fileList, articleList] = await Promise.all([api.listFiles(), api.listArticles()]);
    setFiles(fileList);
    setSelectedIds((prev) =>
      prev.length > 0 ? prev : fileList.filter((file) => file.is_default_reference).map((file) => file.id),
    );
    setArticles(articleList);

    const newest = articleList[0];
    if (newest && !currentArticleId) {
      setCurrentArticleId(newest.id);
      const imageList = await api.listArticleImages(newest.id);
      setImages(imageList);
      if (imageList.some((image) => image.status === "queued" || image.status === "generating")) {
        setPollingImageArticleId(newest.id);
      }
      setContent(newest.content || "");
    } else if (!newest) {
      setImages([]);
    }
  };

  useEffect(() => {
    load().catch((err: Error) => setStatus(`初始化失敗：${err.message}`));
  }, []);

  useEffect(() => {
    if (!pollingArticleId) return;

    const timer = window.setInterval(async () => {
      try {
        const latest = await api.getArticle(pollingArticleId);
        setArticles((prev) => {
          const exists = prev.some((item) => item.id === latest.id);
          if (!exists) {
            return [latest, ...prev];
          }
          return prev.map((item) => (item.id === latest.id ? latest : item));
        });

        if (latest.id === currentArticleId) {
          setContent(latest.content || "");
        }

        if (latest.generation_status === "generated") {
          setStatus("文章生成完成");
          setPollingArticleId(null);
          await refreshImages(latest.id);
        } else if (latest.generation_status === "failed") {
          setStatus(`生成失敗：${latest.generation_error || "背景任務失敗，請稍後再試"}`);
          setPollingArticleId(null);
        } else if (latest.generation_status === "generating") {
          setStatus("文章生成中，請稍候...");
        } else if (latest.generation_status === "queued") {
          setStatus("已加入生成佇列，等待處理中...");
        }
      } catch (err) {
        setStatus(`狀態更新失敗：${(err as Error).message}`);
        setPollingArticleId(null);
      }
    }, 2500);

    return () => window.clearInterval(timer);
  }, [currentArticleId, pollingArticleId]);

  useEffect(() => {
    if (!pollingImageArticleId) return;

    const timer = window.setInterval(async () => {
      try {
        const latestImages = await api.listArticleImages(pollingImageArticleId);
        setImages(latestImages);

        const hasQueued = latestImages.some((image) => image.status === "queued");
        const hasGenerating = latestImages.some((image) => image.status === "generating");
        const hasFailed = latestImages.some((image) => image.status === "failed");
        const allGenerated = latestImages.length > 0 && latestImages.every((image) => image.status === "generated");

        if (hasGenerating) {
          setStatus("圖片生成中，請稍候...");
          return;
        }

        if (hasQueued) {
          setStatus("圖片已加入生成佇列，等待處理中...");
          return;
        }

        if (allGenerated) {
          setStatus("圖片生成完成");
          setPollingImageArticleId(null);
          return;
        }

        if (hasFailed) {
          setStatus("部分圖片生成失敗，請檢查圖片卡片上的錯誤訊息");
          setPollingImageArticleId(null);
        }
      } catch (err) {
        setStatus(`圖片狀態更新失敗：${(err as Error).message}`);
        setPollingImageArticleId(null);
      }
    }, 2500);

    return () => window.clearInterval(timer);
  }, [pollingImageArticleId]);

  const refreshImages = async (articleId: number) => {
    const imageList = await api.listArticleImages(articleId);
    setImages(imageList);
    if (imageList.some((image) => image.status === "queued" || image.status === "generating")) {
      setPollingImageArticleId(articleId);
    }
  };

  const toggleFile = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const onSelectTemplate = (value: string) => {
    setTemplateKey(value);
    const selected = PROMPT_TEMPLATES.find((template) => template.key === value);
    if (selected) {
      setPrompt(selected.value);
    }
  };

  const expandPrompt = async () => {
    if (!promptRequirement.trim()) {
      setStatus("請先輸入一句話需求");
      return;
    }

    setStatus("提示詞擴寫中...");
    setLoadingPrompt(true);
    try {
      const result = await api.expandPrompt({ requirement: promptRequirement.trim() });
      setPrompt(result.prompt);
      setStatus("提示詞生成成功");
    } catch (err) {
      setStatus(`提示詞擴寫失敗：${(err as Error).message}`);
    } finally {
      setLoadingPrompt(false);
    }
  };

  const generate = async () => {
    if (!topic || !outline) {
      setStatus("請輸入主題與大綱");
      return;
    }

    setStatus("生成中...");
    setLoadingArticle(true);
    try {
      const article = await api.generateArticle({
        topic,
        outline,
        selected_file_ids: selectedIds,
        prompt: prompt || undefined,
      });
      setContent(article.content || "");
      setCurrentArticleId(article.id);
      setArticles((prev) => {
        const exists = prev.some((item) => item.id === article.id);
        if (!exists) {
          return [article, ...prev];
        }
        return prev.map((item) => (item.id === article.id ? article : item));
      });
      setStatus("已加入生成佇列，等待處理中...");
      setPollingArticleId(article.id);
      await load();
    } catch (err) {
      setStatus(`生成失敗：${(err as Error).message}`);
    } finally {
      setLoadingArticle(false);
    }
  };

  const generateImages = async () => {
    if (!currentArticleId) {
      setStatus("請先生成文章");
      return;
    }

    setStatus("圖片排隊中...");
    setLoadingImages(true);
    try {
      const result = await api.generateArticleImages(currentArticleId, {
        style_preset: selectedImageStyle,
        output_size: selectedImageSize,
        custom_prompt: prompt,
        need_text_overlay: needTextOverlay,
        text_language: imageTextLanguage,
        text_content: imageTextContent || topic,
      });
      setImages(result);
      setStatus("已加入圖片生成佇列，等待處理中...");
      setPollingImageArticleId(currentArticleId);
    } catch (err) {
      setStatus(`生成圖片失敗：${(err as Error).message}`);
    } finally {
      setLoadingImages(false);
    }
  };

  const imageStatusLabel = (imageStatus: string) => {
    if (imageStatus === "queued") return "排隊中";
    if (imageStatus === "generating") return "生成中";
    if (imageStatus === "generated") return "已完成";
    if (imageStatus === "failed") return "失敗";
    return imageStatus;
  };

  const imageStatusClass = (imageStatus: string) => {
    if (imageStatus === "queued") return "border-amber-200 bg-amber-50 text-amber-800";
    if (imageStatus === "generating") return "border-sky-200 bg-sky-50 text-sky-800";
    if (imageStatus === "generated") return "border-emerald-200 bg-emerald-50 text-emerald-800";
    if (imageStatus === "failed") return "border-rose-200 bg-rose-50 text-rose-700";
    return "border-slate-200 bg-slate-50 text-slate-700";
  };

  const saveContent = async () => {
    if (!currentArticleId) {
      setStatus("請先生成文章");
      return;
    }

    setStatus("儲存中...");
    setSavingContent(true);
    try {
      const updated = await api.updateArticle(currentArticleId, content);
      setStatus("儲存成功");
      setArticles((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setStatus(`儲存失敗：${(err as Error).message}`);
    } finally {
      setSavingContent(false);
    }
  };

  const exportToGoogleSheets = async () => {
    if (!currentArticleId) {
      setStatus("請先生成文章");
      return;
    }
    if (!content.trim()) {
      setStatus("文章內容為空，無法上傳到 Google Sheets");
      return;
    }
    if (sheetDestinations.length === 0) {
      setStatus("請先到系統設定新增 Google Sheets 目的地");
      return;
    }

    setStatus("上傳 Google Sheets 中...");
    setExportingSheet(true);
    try {
      const result = await api.exportArticleToGoogleSheets(currentArticleId, selectedSheetDestinationId || undefined);
      setStatus(`${result.message}：${result.destination_label} / ${result.updated_range || result.sheet_name}`);
    } catch (err) {
      setStatus(`上傳 Google Sheets 失敗：${(err as Error).message}`);
    } finally {
      setExportingSheet(false);
    }
  };

  const publish = async (channel: "website" | "social") => {
    if (!currentArticleId) {
      setStatus("請先生成文章");
      return;
    }
    setStatus("發布中...");
    setPublishingChannel(channel);

    try {
      const result =
        channel === "website" ? await api.publishWebsite(currentArticleId) : await api.publishSocial(currentArticleId);
      setStatus(result.message);
      await load();
    } catch (err) {
      setStatus(`發布失敗：${(err as Error).message}`);
    } finally {
      setPublishingChannel(null);
    }
  };

  const hasActiveAccess = !!entitlements?.is_active;
  const showAccessWarning = entitlements !== null && !entitlements.is_active;

  return (
    <section className="space-y-5 max-w-6xl">
      <div className="card-surface p-6 space-y-2">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="text-2xl font-bold">文章創作與發布</h2>
          <span className="brand-pill">Created by Eric</span>
        </div>
        <p className="text-slate-700">從提示詞、生成、編修到發布，一頁完成內容工作流。</p>
      </div>

      {showAccessWarning && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-5 text-amber-900">
          <p className="text-sm font-semibold">目前尚未開通可用方案</p>
          <p className="mt-1 text-sm">生成提示詞、文章、圖片與發布功能都需要先啟用 7 天試用或完成付款。</p>
          <Link href="/billing" className="mt-3 inline-flex rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white">
            前往訂閱與付款
          </Link>
        </div>
      )}

      <div className="card-surface p-6 space-y-4">
        <h3 className="text-lg font-semibold">區塊一：輸入生成條件</h3>

        <div>
          <p className="text-sm font-medium mb-1">選擇參考檔案</p>
          <div className="flex flex-wrap gap-2">
            {files.map((file) => (
              <button
                key={file.id}
                type="button"
                onClick={() => toggleFile(file.id)}
                className={`rounded-full border px-3 py-1 text-sm transition ${
                  selectedIds.includes(file.id)
                    ? "border-[#f09a29] bg-[linear-gradient(135deg,#ffbe0b,#ff7b00)] text-white"
                    : "bg-white/80 text-slate-700 border-[var(--line)] hover:bg-[#fff0c9]"
                }`}
              >
                {file.file_name}
              </button>
            ))}
          </div>
        </div>

        <label className="block text-sm font-medium">
          選擇提示詞範本
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            value={templateKey}
            onChange={(e) => onSelectTemplate(e.target.value)}
          >
            <option value="">請選擇範本</option>
            {PROMPT_TEMPLATES.map((template) => (
              <option key={template.key} value={template.key}>
                {template.label}
              </option>
            ))}
          </select>
        </label>

        <div className="rounded-xl border border-[var(--line)] bg-[linear-gradient(135deg,#fff6da,#ffe2af)] p-4 space-y-2">
          <label className="block text-sm font-medium">
            一句話需求（AI 會幫你擴寫成精準提示詞）
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              value={promptRequirement}
              onChange={(e) => setPromptRequirement(e.target.value)}
              placeholder="例如：我要寫給中小企業老闆看的品牌定位教學"
            />
          </label>
          <button
            type="button"
            onClick={expandPrompt}
            className="brand-btn-secondary px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!hasActiveAccess || loadingPrompt}
          >
            {loadingPrompt ? "生成中..." : "生成精準提示詞"}
          </button>
        </div>

        <label className="block text-sm font-medium">
          主要提示詞
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            rows={5}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="可手動輸入，或用上方範本/擴寫功能自動帶入"
          />
        </label>

        <label className="block text-sm font-medium">
          主題
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </label>

        <label className="block text-sm font-medium">
          大綱
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            rows={6}
            value={outline}
            onChange={(e) => setOutline(e.target.value)}
          />
        </label>

        {status && <p className="rounded-xl border border-[var(--line)] bg-[rgba(255,247,221,0.9)] px-4 py-3 text-sm text-slate-700">{status}</p>}

        <button
          onClick={generate}
          className="brand-btn px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!hasActiveAccess || loadingArticle || loadingPrompt}
        >
          {loadingArticle ? "生成中..." : "生成文章"}
        </button>
      </div>

      <div className="card-surface p-6 space-y-4">
        <h3 className="text-lg font-semibold">區塊二：文章編輯區</h3>
        <textarea
          className="w-full min-h-[360px] rounded-lg border border-slate-300 p-3"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="生成結果會顯示在此，可手動編輯"
        />
        <button
          onClick={saveContent}
          className="brand-btn-secondary px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!hasActiveAccess || savingContent}
        >
          {savingContent ? "儲存中..." : "儲存修改"}
        </button>
      </div>

      <div className="card-surface p-6 space-y-4">
        <h3 className="text-lg font-semibold">區塊三：發布 + 配圖</h3>

        <div className="rounded-xl border border-[var(--line)] bg-[linear-gradient(135deg,#fff5d3,#ffdca1)] p-4 space-y-3">
          <p className="text-sm font-semibold text-[var(--text)]">AI 圖片生成（中文文字需求自動走 nano banana）</p>
          <p className="text-xs text-slate-600">系統會自動選最合理路徑：可用時優先走 OpenAI 真實生圖，不可用時自動退回預覽 mock 圖。</p>
          <div className="grid md:grid-cols-3 gap-3">
            <label className="block text-sm font-medium">
              圖片風格
              <select
                className="mt-1 w-full rounded-lg border border-slate-300 p-2"
                value={selectedImageStyle}
                onChange={(e) => setSelectedImageStyle(e.target.value)}
              >
                {stylePresets.map((preset) => (
                  <option key={preset.key} value={preset.key}>
                    {preset.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm font-medium">
              社群尺寸
              <select
                className="mt-1 w-full rounded-lg border border-slate-300 p-2"
                value={selectedImageSize}
                onChange={(e) => setSelectedImageSize(e.target.value)}
              >
                {sizePresets.map((preset) => (
                  <option key={preset.key} value={preset.key}>
                    {preset.label}（{preset.size}）
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm font-medium">
              文字語言
              <select
                className="mt-1 w-full rounded-lg border border-slate-300 p-2"
                value={imageTextLanguage}
                onChange={(e) => setImageTextLanguage(e.target.value)}
              >
                <option value="zh-Hant">繁體中文</option>
                <option value="en">英文</option>
                <option value="none">無文字</option>
              </select>
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={needTextOverlay} onChange={(e) => setNeedTextOverlay(e.target.checked)} />
            圖片需要文字排版
          </label>

          <label className="block text-sm font-medium">
            圖上文字內容
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              value={imageTextContent}
              onChange={(e) => setImageTextContent(e.target.value)}
              placeholder="例如：AI 內容工作流完整指南"
            />
          </label>

          <button
            onClick={generateImages}
            className="brand-btn px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!hasActiveAccess || loadingImages}
          >
            {loadingImages ? "生成中..." : "生成相符配圖"}
          </button>
        </div>

        {images.length > 0 && (
          <div className="grid md:grid-cols-2 gap-3">
            {images.map((image) => (
              <div key={image.id} className="rounded-xl border border-[var(--line)] bg-white p-3 space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${imageStatusClass(image.status)}`}>
                    {imageStatusLabel(image.status)}
                  </span>
                  <p className="text-xs text-slate-600">
                    provider: {image.provider} / model: {image.model}
                  </p>
                </div>
                {image.image_url ? (
                  <img
                    src={image.image_url}
                    alt={`article-image-${image.id}`}
                    className="w-full rounded-lg border border-slate-200"
                  />
                ) : (
                  <div className="flex aspect-[3/2] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
                    {image.status === "failed" ? "圖片生成失敗" : "圖片生成中，請稍候..."}
                  </div>
                )}
                <p className="text-xs text-slate-600">
                  style: {image.style_preset}
                  {" / "}
                  size: {image.width}x{image.height}
                </p>
                {image.provider === "nano_banana" && (
                  <p className="text-xs text-slate-500">這張是預覽 mock 圖，用來確認構圖與文案位置。</p>
                )}
                {image.generation_error && <p className="text-xs text-rose-600">錯誤原因：{image.generation_error}</p>}
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-3 flex-wrap">
          <label className="block min-w-[240px] text-sm font-medium">
            Google Sheets 目的地
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              value={selectedSheetDestinationId || ""}
              onChange={(e) => setSelectedSheetDestinationId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">使用預設目的地</option>
              {sheetDestinations.map((destination) => (
                <option key={destination.id} value={destination.id}>
                  {destination.label} / {destination.sheet_name}
                </option>
              ))}
            </select>
          </label>
          <button
            onClick={exportToGoogleSheets}
            className="brand-btn-secondary self-end px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!hasActiveAccess || exportingSheet || sheetDestinations.length === 0}
          >
            {exportingSheet ? "上傳中..." : "上傳到 Google Sheets"}
          </button>
          <button
            onClick={() => publish("website")}
            className="brand-btn self-end px-4 py-2"
            disabled={!hasActiveAccess || publishingChannel !== null}
          >
            {publishingChannel === "website" ? "發布中..." : "發布至個人網頁"}
          </button>
          <button
            onClick={() => publish("social")}
            className="brand-btn-secondary self-end px-4 py-2"
            disabled={!hasActiveAccess || publishingChannel !== null}
          >
            {publishingChannel === "social" ? "發布中..." : "發布至社交平台"}
          </button>
        </div>

        {currentArticle && (
          <p className="text-sm text-slate-600">
            目前文章狀態：生成 {currentArticle.generation_status} / 網頁 {currentArticle.published_to_website ? "已發布" : "未發布"} / 社交平台{" "}
            {currentArticle.published_to_social ? "已發布" : "未發布"}
          </p>
        )}

        {currentArticle?.generation_error && (
          <p className="text-sm text-red-600">錯誤原因：{currentArticle.generation_error}</p>
        )}

        {status && <p className="text-sm text-slate-700">{status}</p>}
      </div>
    </section>
  );
}
