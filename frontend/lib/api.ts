import { clearToken, getToken } from "@/lib/auth";
import {
  AdminRecentPayment,
  AdminRecentUser,
  AdminStats,
  Article,
  ArticleImage,
  AuthResponse,
  CheckoutResponse,
  Entitlements,
  ImageSettings,
  ImageStylePreset,
  KnowledgeFile,
  ModelCatalogItem,
  Plan,
  Settings,
  Subscription,
} from "@/lib/types";

const REQUEST_TIMEOUT_MS = 90000;

function resolveApiBase(): string {
  const configuredBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configuredBase) {
    return configuredBase;
  }

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8001/api`;
  }

  return "http://127.0.0.1:8001/api";
}

async function parseErrorPayload(res: Response): Promise<Record<string, unknown>> {
  return res.json().catch(() => ({}));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const baseHeaders: HeadersInit = {
    ...(init?.headers || {}),
  };

  const token = typeof window !== "undefined" ? getToken() : null;
  if (token) {
    (baseHeaders as Record<string, string>).Authorization = `Bearer ${token}`;
  }

  if (!(init?.body instanceof FormData)) {
    (baseHeaders as Record<string, string>)["Content-Type"] = "application/json";
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let res: Response;
  try {
    const apiBase = resolveApiBase();
    res = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: baseHeaders,
      cache: "no-store",
      signal: controller.signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      throw new Error("請求逾時。AI 生成可能需要較久時間，請稍後再試，或改用較快的模型。");
    }
    throw new Error("無法連線到後端 API，請確認前端與後端都已啟動，且後端位址設定正確");
  } finally {
    clearTimeout(timeout);
  }

  if (!res.ok) {
    const payload = await parseErrorPayload(res);
    if (res.status === 401) {
      clearToken();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    const detail = typeof payload.detail === "string" ? payload.detail : "";
    if (res.status === 402) {
      throw new Error(detail || "目前尚未開通可用方案，請先到「訂閱與付款」啟用 7 天試用或完成付款");
    }
    if (res.status >= 500) {
      throw new Error(detail || `伺服器暫時發生錯誤（HTTP ${res.status}）`);
    }
    throw new Error(detail || `API 呼叫失敗（HTTP ${res.status}）`);
  }

  return res.json();
}

export const api = {
  register: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/login", { method: "POST", body: JSON.stringify(payload) }),
  forgotPassword: (payload: { email: string }) =>
    request<{ message: string; reset_token?: string }>("/forgot-password", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  resetPassword: (payload: { token: string; new_password: string }) =>
    request<{ success: boolean; message: string }>("/reset-password", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSettings: () => request<Settings | null>("/settings"),
  saveSettings: (payload: Partial<Settings>) =>
    request<Settings>("/settings", { method: "PUT", body: JSON.stringify(payload) }),
  getModelCatalog: () => request<{ models: ModelCatalogItem[] }>("/settings/model-catalog"),

  getImageSettings: () => request<ImageSettings>("/image-settings"),
  saveImageSettings: (payload: Partial<ImageSettings>) =>
    request<ImageSettings>("/image-settings", { method: "PUT", body: JSON.stringify(payload) }),
  getImageStylePresets: () => request<ImageStylePreset[]>("/image-style-presets"),

  listPlans: () => request<Plan[]>("/billing/plans"),
  getSubscription: () => request<Subscription>("/billing/subscription"),
  getEntitlements: () => request<Entitlements>("/billing/entitlements"),
  startTrial: () => request<{ success: boolean; message: string; expires_at: string }>("/billing/trial/start", { method: "POST" }),
  createCheckout: (payload: { plan_code: string; provider?: string }) =>
    request<CheckoutResponse>("/billing/checkout", { method: "POST", body: JSON.stringify(payload) }),
  mockMarkPaid: (payload: { txn_id: string; status: string }) =>
    request<{ success: boolean; message: string }>("/billing/webhook/payment", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listFiles: () => request<KnowledgeFile[]>("/knowledge-files"),
  uploadFile: async (file: File, includeAsDefaultReference = true) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("include_as_default_reference", String(includeAsDefaultReference));
    return request<KnowledgeFile>("/knowledge-files", { method: "POST", body: formData });
  },
  updateFileDefaultReference: (fileId: number, isDefaultReference: boolean) =>
    request<KnowledgeFile>(`/knowledge-files/${fileId}/default-reference`, {
      method: "PATCH",
      body: JSON.stringify({ is_default_reference: isDefaultReference }),
    }),
  deleteFile: (fileId: number) =>
    request<{ success: boolean; message: string; file_id: number }>(`/knowledge-files/${fileId}`, {
      method: "DELETE",
    }),

  listArticles: () => request<Article[]>("/articles"),
  getArticle: (id: number) => request<Article>(`/articles/${id}`),
  expandPrompt: (payload: { requirement: string; model?: string }) =>
    request<{ prompt: string }>("/articles/prompt-expand", { method: "POST", body: JSON.stringify(payload) }),
  generateArticle: (payload: {
    topic: string;
    outline: string;
    selected_file_ids: number[];
    model?: string;
    prompt?: string;
  }) => request<Article>("/articles/generate", { method: "POST", body: JSON.stringify(payload) }),
  updateArticle: (id: number, content: string) =>
    request<Article>(`/articles/${id}`, { method: "PUT", body: JSON.stringify({ content }) }),

  generateArticleImages: (
    articleId: number,
    payload: {
      style_preset: string;
      custom_prompt?: string;
      need_text_overlay?: boolean;
      text_language?: string;
      text_content?: string;
      num_images?: number;
    },
  ) => request<ArticleImage[]>(`/articles/${articleId}/generate-images`, { method: "POST", body: JSON.stringify(payload) }),
  listArticleImages: (articleId: number) => request<ArticleImage[]>(`/articles/${articleId}/images`),

  publishWebsite: (id: number) => request<{ message: string }>(`/publish/website/${id}`, { method: "POST" }),
  publishSocial: (id: number) => request<{ message: string }>(`/publish/social/${id}`, { method: "POST" }),

  getAdminStats: (adminKey: string) =>
    request<AdminStats>("/admin/stats", { headers: { "X-Admin-Key": adminKey } }),
  listAdminRecentUsers: (adminKey: string, limit = 10) =>
    request<AdminRecentUser[]>(`/admin/recent-users?limit=${limit}`, { headers: { "X-Admin-Key": adminKey } }),
  listAdminRecentPayments: (adminKey: string, limit = 10) =>
    request<AdminRecentPayment[]>(`/admin/recent-payments?limit=${limit}`, {
      headers: { "X-Admin-Key": adminKey },
    }),
};
