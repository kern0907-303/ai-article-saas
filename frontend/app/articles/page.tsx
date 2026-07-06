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
  Workspace,
} from "@/lib/types";

const KNOWLEDGE_CATEGORIES = [
  { key: "writing_skill", label: "寫作 Skill" },
  { key: "brand_voice", label: "品牌語氣" },
  { key: "product_info", label: "產品資料" },
  { key: "audience_profile", label: "受眾輪廓" },
  { key: "case_study", label: "案例" },
  { key: "offer", label: "方案/Offer" },
  { key: "forbidden_rules", label: "禁用規則" },
  { key: "reference_material", label: "一般參考" },
  { key: "other", label: "其他" },
];

const KNOWLEDGE_CATEGORY_PRESETS = [
  {
    key: "smart",
    label: "智慧讀取：寫作 Skill + 品牌 + 產品",
    categories: ["writing_skill", "brand_voice", "product_info"],
  },
  {
    key: "writing",
    label: "只讀寫作 Skill",
    categories: ["writing_skill"],
  },
  {
    key: "brand",
    label: "品牌內容：品牌 + 受眾 + 禁用規則",
    categories: ["brand_voice", "audience_profile", "forbidden_rules"],
  },
  {
    key: "sales",
    label: "銷售內容：產品 + Offer + 案例",
    categories: ["product_info", "offer", "case_study"],
  },
  {
    key: "all",
    label: "全部分類",
    categories: KNOWLEDGE_CATEGORIES.map((category) => category.key),
  },
];

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

const ARTICLE_DRAFT_STORAGE_KEY = "ai_article_saas.article_page_draft.v1";

type ArticlePageDraft = {
  selectedImageStyle: string;
  selectedImageSize: string;
  selectedSheetDestinationId: number | null;
  needTextOverlay: boolean;
  imageTextLanguage: string;
  imageTextContent: string;
  selectedIds: number[];
  selectedWorkspaceId: number | null;
  selectedKnowledgeCategories: string[];
  topic: string;
  outline: string;
  prompt: string;
  promptRequirement: string;
  templateKey: string;
  content: string;
  currentArticleId: number | null;
};

const readArticleDraft = (): Partial<ArticlePageDraft> => {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(ARTICLE_DRAFT_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
};

const writeArticleDraft = (draft: ArticlePageDraft) => {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ARTICLE_DRAFT_STORAGE_KEY, JSON.stringify(draft));
};

const isPublicSheetImage = (image: ArticleImage) =>
  image.status === "generated" &&
  !!image.image_url &&
  (image.image_url.startsWith("http://") || image.image_url.startsWith("https://"));

const isSheetSelectableImage = (image: ArticleImage) =>
  image.status === "generated" &&
  !!image.image_url &&
  (image.image_url.startsWith("http://") || image.image_url.startsWith("https://") || image.image_url.startsWith("data:image/"));

const imageFileExtension = (imageUrl: string) => {
  const dataMatch = imageUrl.match(/^data:image\/(png|jpeg|jpg|webp);/);
  if (dataMatch) return dataMatch[1] === "jpeg" ? "jpg" : dataMatch[1];

  try {
    const pathname = new URL(imageUrl).pathname;
    const extension = pathname.split(".").pop()?.toLowerCase();
    if (extension && ["png", "jpg", "jpeg", "webp"].includes(extension)) {
      return extension === "jpeg" ? "jpg" : extension;
    }
  } catch {
    return "png";
  }
  return "png";
};

export default function ArticlesPage() {
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
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
  const [selectedSheetImageIds, setSelectedSheetImageIds] = useState<number[]>([]);
  const [imageSelectionTouched, setImageSelectionTouched] = useState(false);

  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | null>(null);
  const [selectedKnowledgeCategories, setSelectedKnowledgeCategories] = useState<string[]>(["writing_skill", "brand_voice", "product_info"]);
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
  const [draftHydrated, setDraftHydrated] = useState(false);
  const [imageActionKey, setImageActionKey] = useState<string | null>(null);

  const currentArticle = useMemo(
    () => articles.find((item) => item.id === currentArticleId) || null,
    [articles, currentArticleId],
  );
  const sheetSelectableImages = useMemo(() => images.filter(isSheetSelectableImage), [images]);
  const selectedSheetImageLinks = useMemo(
    () =>
      sheetSelectableImages
        .filter((image) => selectedSheetImageIds.includes(image.id))
        .map((image) => image.image_url)
        .filter((url) => url.startsWith("http://") || url.startsWith("https://")),
    [sheetSelectableImages, selectedSheetImageIds],
  );
  const dataModeValue = useMemo(() => {
    const sortedSelected = [...selectedKnowledgeCategories].sort().join(",");
    const matched = KNOWLEDGE_CATEGORY_PRESETS.find(
      (preset) => [...preset.categories].sort().join(",") === sortedSelected,
    );
    return matched?.key || "custom";
  }, [selectedKnowledgeCategories]);

  useEffect(() => {
    const selectableIds = sheetSelectableImages.map((image) => image.id);
    setSelectedSheetImageIds((prev) =>
      imageSelectionTouched ? prev.filter((id) => selectableIds.includes(id)) : selectableIds,
    );
  }, [imageSelectionTouched, sheetSelectableImages]);

  useEffect(() => {
    setImageSelectionTouched(false);
    setSelectedSheetImageIds([]);
  }, [currentArticleId]);

  useEffect(() => {
    const draft = readArticleDraft();
    if (typeof draft.selectedImageStyle === "string") setSelectedImageStyle(draft.selectedImageStyle);
    if (typeof draft.selectedImageSize === "string") setSelectedImageSize(draft.selectedImageSize);
    if (typeof draft.selectedSheetDestinationId === "number" || draft.selectedSheetDestinationId === null) {
      setSelectedSheetDestinationId(draft.selectedSheetDestinationId);
    }
    if (typeof draft.needTextOverlay === "boolean") setNeedTextOverlay(draft.needTextOverlay);
    if (typeof draft.imageTextLanguage === "string") setImageTextLanguage(draft.imageTextLanguage);
    if (typeof draft.imageTextContent === "string") setImageTextContent(draft.imageTextContent);
    if (Array.isArray(draft.selectedIds)) setSelectedIds(draft.selectedIds.filter((id) => typeof id === "number"));
    if (typeof draft.selectedWorkspaceId === "number" || draft.selectedWorkspaceId === null) {
      setSelectedWorkspaceId(draft.selectedWorkspaceId);
    }
    if (Array.isArray(draft.selectedKnowledgeCategories)) {
      setSelectedKnowledgeCategories(draft.selectedKnowledgeCategories.filter((item) => typeof item === "string"));
    }
    if (typeof draft.topic === "string") setTopic(draft.topic);
    if (typeof draft.outline === "string") setOutline(draft.outline);
    if (typeof draft.prompt === "string") setPrompt(draft.prompt);
    if (typeof draft.promptRequirement === "string") setPromptRequirement(draft.promptRequirement);
    if (typeof draft.templateKey === "string") setTemplateKey(draft.templateKey);
    if (typeof draft.content === "string") setContent(draft.content);
    if (typeof draft.currentArticleId === "number" || draft.currentArticleId === null) {
      setCurrentArticleId(draft.currentArticleId);
    }
    setDraftHydrated(true);
  }, []);

  useEffect(() => {
    if (!draftHydrated) return;
    writeArticleDraft({
      selectedImageStyle,
      selectedImageSize,
      selectedSheetDestinationId,
      needTextOverlay,
      imageTextLanguage,
      imageTextContent,
      selectedIds,
      selectedWorkspaceId,
      selectedKnowledgeCategories,
      topic,
      outline,
      prompt,
      promptRequirement,
      templateKey,
      content,
      currentArticleId,
    });
  }, [
    content,
    currentArticleId,
    draftHydrated,
    imageTextContent,
    imageTextLanguage,
    needTextOverlay,
    outline,
    prompt,
    promptRequirement,
    selectedIds,
    selectedKnowledgeCategories,
    selectedWorkspaceId,
    selectedImageSize,
    selectedImageStyle,
    selectedSheetDestinationId,
    templateKey,
    topic,
  ]);

  const load = async () => {
    const [presets, sizes, sheets, workspaceData, entitlementData] = await Promise.all([
      api.getImageStylePresets(),
      api.getImageSizePresets(),
      api.listGoogleSheetDestinations(),
      api.listWorkspaces(),
      api.getEntitlements(),
    ]);
    setStylePresets(presets);
    setSizePresets(sizes);
    setSheetDestinations(sheets);
    setWorkspaces(workspaceData);
    setSelectedWorkspaceId((prev) => prev || workspaceData.find((item) => item.is_default)?.id || workspaceData[0]?.id || null);
    setSelectedSheetDestinationId((prev) => prev || sheets.find((item) => item.is_default)?.id || sheets[0]?.id || null);
    setEntitlements(entitlementData);

    if (!entitlementData.is_active) {
      setFiles([]);
      setArticles([]);
      setImages([]);
      setCurrentArticleId(null);
      return;
    }

    const effectiveWorkspaceId = selectedWorkspaceId || workspaceData.find((item) => item.is_default)?.id || workspaceData[0]?.id || null;
    const [fileList, articleList] = await Promise.all([api.listFiles({ workspace_id: effectiveWorkspaceId }), api.listArticles()]);
    setFiles(fileList);
    setSelectedIds((prev) =>
      prev.length > 0 ? prev : fileList.filter((file) => file.is_default_reference).map((file) => file.id),
    );
    setArticles(articleList);

    const newest = articleList[0];
    const activeArticle = (currentArticleId && articleList.find((article) => article.id === currentArticleId)) || newest;
    if (activeArticle) {
      if (!currentArticleId) {
        setCurrentArticleId(activeArticle.id);
      }
      const imageList = await api.listArticleImages(activeArticle.id);
      setImages(imageList);
      if (imageList.some((image) => image.status === "queued" || image.status === "generating")) {
        setPollingImageArticleId(activeArticle.id);
      }
      setTopic((prev) => prev || activeArticle.topic || "");
      setOutline((prev) => prev || activeArticle.outline || "");
      setContent((prev) => prev || activeArticle.content || "");
    } else {
      setImages([]);
    }
  };

  useEffect(() => {
    if (!draftHydrated) return;
    load().catch((err: Error) => setStatus(`初始化失敗：${err.message}`));
  }, [draftHydrated, selectedWorkspaceId]);

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

  const toggleKnowledgeCategory = (key: string) => {
    setSelectedKnowledgeCategories((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    );
  };

  const toggleSheetImage = (id: number) => {
    setImageSelectionTouched(true);
    setSelectedSheetImageIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const downloadImage = async (image: ArticleImage) => {
    if (!image.image_url) {
      setStatus("這張圖片目前沒有可下載的圖片資料");
      return;
    }

    const filename = `article-${currentArticleId || "draft"}-image-${image.id}-${image.width}x${image.height}.${imageFileExtension(
      image.image_url,
    )}`;

    const triggerDownload = (url: string) => {
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    };

    try {
      if (image.image_url.startsWith("data:image/")) {
        triggerDownload(image.image_url);
        setStatus(`圖片已下載：${filename}`);
        return;
      }

      const response = await fetch(image.image_url);
      if (!response.ok) throw new Error("圖片下載失敗");
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      triggerDownload(objectUrl);
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      setStatus(`圖片已下載：${filename}`);
    } catch {
      window.open(image.image_url, "_blank", "noopener,noreferrer");
      setStatus("瀏覽器已開啟圖片，若未自動下載請在圖片上按右鍵另存");
    }
  };

  const updateImageRecord = (updated: ArticleImage) => {
    setImages((prev) => prev.map((image) => (image.id === updated.id ? updated : image)));
  };

  const uploadImageToPcloud = async (image: ArticleImage) => {
    setImageActionKey(`upload-${image.id}`);
    setStatus("圖片上傳 pCloud 中...");
    try {
      const updated = await api.uploadArticleImageToPcloud(image.id);
      updateImageRecord(updated);
      setStatus("圖片已上傳 pCloud，並取得公開連結");
    } catch (err) {
      setStatus(`圖片上傳 pCloud 失敗：${(err as Error).message}`);
    } finally {
      setImageActionKey(null);
    }
  };

  const createImagePublicLink = async (image: ArticleImage) => {
    setImageActionKey(`link-${image.id}`);
    setStatus("產生圖片連結中...");
    try {
      const updated = await api.createArticleImagePublicLink(image.id);
      updateImageRecord(updated);
      if (updated.image_url.startsWith("http://") || updated.image_url.startsWith("https://")) {
        await navigator.clipboard?.writeText(updated.image_url);
        setStatus("圖片公開連結已產生並複製");
      } else {
        setStatus("圖片已處理，但尚未取得公開網址");
      }
    } catch (err) {
      setStatus(`產生圖片連結失敗：${(err as Error).message}`);
    } finally {
      setImageActionKey(null);
    }
  };

  const onSelectTemplate = (value: string) => {
    setTemplateKey(value);
    const selected = PROMPT_TEMPLATES.find((template) => template.key === value);
    if (selected) {
      setPrompt(selected.value);
    }
  };

  const onSelectDataMode = (value: string) => {
    const selected = KNOWLEDGE_CATEGORY_PRESETS.find((preset) => preset.key === value);
    if (selected) {
      setSelectedKnowledgeCategories(selected.categories);
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
        use_default_references: true,
        workspace_id: selectedWorkspaceId,
        knowledge_categories: selectedKnowledgeCategories,
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
      setImageSelectionTouched(false);
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
      const result = await api.exportArticleToGoogleSheets(currentArticleId, selectedSheetDestinationId || undefined, {
        fallback_topic: currentArticle?.topic || topic || "未命名文章",
        fallback_outline: currentArticle?.outline || outline || "",
        fallback_content: content,
        fallback_generation_model: currentArticle?.generation_model || "",
        fallback_generation_status: currentArticle?.generation_status || "generated",
        fallback_image_links: selectedSheetImageLinks,
        selected_image_ids: selectedSheetImageIds,
      });
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
          <span className="brand-pill">AI Article SaaS</span>
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
        <div>
          <h3 className="text-lg font-semibold">開始寫文章</h3>
          <p className="mt-1 text-sm text-slate-600">先選模式、填主題和大綱，就可以生成；其他細節先不用管。</p>
        </div>

        <div className="grid md:grid-cols-2 gap-3">
          <label className="block text-sm font-medium">
            品牌 / 專案
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              value={selectedWorkspaceId || ""}
              onChange={(e) => {
                setSelectedWorkspaceId(e.target.value ? Number(e.target.value) : null);
                setSelectedIds([]);
              }}
            >
              <option value="">使用一般資料</option>
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}{workspace.is_default ? "（預設）" : ""}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-medium">
            寫作模式
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
              value={templateKey}
              onChange={(e) => onSelectTemplate(e.target.value)}
            >
              <option value="">自動判斷</option>
              {PROMPT_TEMPLATES.map((template) => (
                <option key={template.key} value={template.key}>
                  {template.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="block text-sm font-medium">
          文章主題
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="例如：小品牌如何用 AI 建立穩定內容產線"
          />
        </label>

        <label className="block text-sm font-medium">
          大綱或重點
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            rows={5}
            value={outline}
            onChange={(e) => setOutline(e.target.value)}
            placeholder={"可以用條列：\n1. 目前卡在哪\n2. 三個解法\n3. 結尾 CTA"}
          />
        </label>

        <details className="rounded-xl border border-[var(--line)] bg-white/60 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-[var(--text)]">進階設定：知識庫、提示詞、指定參考檔</summary>
          <div className="mt-4 space-y-4">
            <div className="grid md:grid-cols-2 gap-3">
              <label className="block text-sm font-medium">
                資料讀取模式
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 p-2"
                  value={dataModeValue}
                  onChange={(e) => onSelectDataMode(e.target.value)}
                >
                  {KNOWLEDGE_CATEGORY_PRESETS.map((preset) => (
                    <option key={preset.key} value={preset.key}>
                      {preset.label}
                    </option>
                  ))}
                  <option value="custom">自訂分類</option>
                </select>
              </label>

              <label className="block text-sm font-medium">
                指定參考檔
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 p-2"
                  value={selectedIds[0] || ""}
                  onChange={(e) => setSelectedIds(e.target.value ? [Number(e.target.value)] : [])}
                >
                  <option value="">自動使用預設參考檔</option>
                  {files.map((file) => (
                    <option key={file.id} value={file.id}>
                      {file.file_name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div>
              <p className="text-sm font-medium mb-2">自訂資料分類</p>
              <div className="flex flex-wrap gap-2">
                {KNOWLEDGE_CATEGORIES.map((category) => (
                  <button
                    key={category.key}
                    type="button"
                    onClick={() => toggleKnowledgeCategory(category.key)}
                    className={`rounded-full border px-3 py-1 text-sm transition ${
                      selectedKnowledgeCategories.includes(category.key)
                        ? "border-emerald-500 bg-emerald-50 text-emerald-800"
                        : "bg-white/80 text-slate-700 border-[var(--line)] hover:bg-emerald-50"
                    }`}
                  >
                    {category.label}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                只會讀取目前品牌/專案與所選分類資料，不會跨帳號或跨品牌混用。
              </p>
            </div>

            {files.length > 1 && (
              <details className="rounded-lg border border-dashed border-[var(--line)] bg-white/70 p-3">
                <summary className="cursor-pointer text-sm font-medium">同時指定多份參考檔</summary>
                <div className="mt-3 flex flex-wrap gap-2">
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
              </details>
            )}

            <div className="rounded-xl border border-[var(--line)] bg-[linear-gradient(135deg,#fff6da,#ffe2af)] p-4 space-y-2">
              <label className="block text-sm font-medium">
                一句話需求
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
                {loadingPrompt ? "生成中..." : "幫我擴寫提示詞"}
              </button>
            </div>

            <label className="block text-sm font-medium">
              主要提示詞
              <textarea
                className="mt-1 w-full rounded-lg border border-slate-300 p-2"
                rows={5}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="可手動輸入，或用寫作模式/擴寫功能自動帶入"
              />
            </label>
          </div>
        </details>

        {files.length === 0 && (
          <p className="rounded-xl border border-dashed border-[var(--line)] bg-white/70 px-4 py-3 text-sm text-slate-600">
            尚未上傳知識庫檔案。可先生成文章；需要固定風格時，再到個人知識庫上傳 Markdown/TXT。
          </p>
        )}

        {status && <p className="rounded-xl border border-[var(--line)] bg-[rgba(255,247,221,0.9)] px-4 py-3 text-sm text-slate-700">{status}</p>}

        <button
          onClick={generate}
          className="brand-btn w-full px-4 py-3 text-base font-semibold disabled:cursor-not-allowed disabled:opacity-60 md:w-auto"
          disabled={!hasActiveAccess || loadingArticle || loadingPrompt}
        >
          {loadingArticle ? "生成中..." : "生成文章"}
        </button>
      </div>

      <div className="card-surface p-6 space-y-4">
        <h3 className="text-lg font-semibold">編輯文章</h3>
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

      <details className="card-surface p-6">
        <summary className="cursor-pointer text-lg font-semibold">配圖、匯出與發布</summary>
        <div className="mt-4 space-y-4">

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
                {image.image_url && (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => downloadImage(image)}
                      className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      下載圖片
                    </button>
                    <button
                      type="button"
                      onClick={() => uploadImageToPcloud(image)}
                      disabled={imageActionKey !== null || !image.image_url.startsWith("data:image/")}
                      className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {imageActionKey === `upload-${image.id}` ? "上傳中..." : "上傳 pCloud"}
                    </button>
                    <button
                      type="button"
                      onClick={() => createImagePublicLink(image)}
                      disabled={imageActionKey !== null}
                      className="rounded-lg border border-emerald-300 px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {imageActionKey === `link-${image.id}` ? "產生中..." : "產生圖片連結"}
                    </button>
                  </div>
                )}
                <label
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${
                    isSheetSelectableImage(image)
                      ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                      : "border-slate-200 bg-slate-50 text-slate-500"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-emerald-600"
                    checked={selectedSheetImageIds.includes(image.id)}
                    disabled={!isSheetSelectableImage(image)}
                    onChange={() => toggleSheetImage(image.id)}
                  />
                  <span>
                    {isPublicSheetImage(image)
                      ? "上傳此圖片連結到 Google Sheets"
                      : image.image_url?.startsWith("data:image/")
                        ? "上傳時先轉成 pCloud 公開連結，再寫入 Google Sheets"
                        : "圖片可下載，但目前沒有公開網址可寫入 Google Sheets"}
                  </span>
                </label>
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
          {sheetSelectableImages.length > 0 && (
            <p className="self-end pb-2 text-xs text-slate-600">
              已勾選 {selectedSheetImageIds.length} / {sheetSelectableImages.length} 張圖片
            </p>
          )}
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
      </details>
    </section>
  );
}
