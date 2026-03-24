export type Settings = {
  id: number;
  user_id: string;
  ai_provider: "openai" | "anthropic" | "gemini" | "github";
  openai_api_key?: string;
  anthropic_api_key?: string;
  gemini_api_key?: string;
  github_api_key?: string;
  website_api_key?: string;
  social_api_key?: string;
  article_model: string;
  prompt_model: string;
  image_model: string;
  website_endpoint?: string;
  social_endpoint?: string;
  notes?: string;
};

export type ModelCatalogItem = {
  key: string;
  provider: string;
  category: string;
  label: string;
  description: string;
  cost_tier: "low" | "medium" | "high";
};

export type KnowledgeFile = {
  id: number;
  user_id: string;
  file_name: string;
  stored_path: string;
  content_type?: string;
  file_size: number;
  extracted_text_preview?: string;
  is_default_reference: boolean;
};

export type Article = {
  id: number;
  user_id: string;
  topic: string;
  outline: string;
  content?: string;
  selected_file_ids?: string;
  generation_model?: string;
  generation_status: string;
  published_to_website: boolean;
  published_to_social: boolean;
  publish_website_result?: string;
  publish_social_result?: string;
};

export type AuthUser = {
  id: number;
  email: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type ImageSettings = {
  id: number;
  user_id: string;
  image_provider_mode: "auto" | "nano_banana" | "openai" | "stability";
  default_provider: "openai" | "stability" | "nano_banana";
  force_nano_banana_for_zh_text: boolean;
  nano_banana_model: string;
  openai_image_model: string;
  default_size: string;
  default_quality: "standard" | "high";
  output_format: "png" | "jpg" | "webp";
  images_per_article: number;
  zh_text_detection_keywords: string;
};

export type ImageStylePreset = {
  key: string;
  label: string;
  description: string;
};

export type ArticleImage = {
  id: number;
  user_id: string;
  article_id: number;
  provider: string;
  model: string;
  style_preset: string;
  prompt: string;
  image_url: string;
  width: number;
  height: number;
  text_language?: string;
  text_content?: string;
  status: string;
};

export type Plan = {
  id: number;
  code: string;
  name: string;
  description?: string;
  duration_days: number;
  price_cents: number;
  currency: string;
  is_trial: number;
};

export type Subscription = {
  status: string;
  access_tier: "inactive" | "trial" | "paid";
  plan_code?: string;
  started_at?: string;
  expires_at?: string;
  is_active: boolean;
  trial_used: boolean;
};

export type CheckoutResponse = {
  payment_id: number;
  txn_id: string;
  amount_cents: number;
  currency: string;
  provider: string;
  status: string;
};

export type Entitlements = {
  status: string;
  access_tier: "inactive" | "trial" | "paid";
  plan_code?: string;
  started_at?: string;
  expires_at?: string;
  is_active: boolean;
  trial_used: boolean;
  limits: {
    article_generate_per_day: number;
    prompt_expand_per_day: number;
    image_generate_per_day: number;
    knowledge_total_bytes: number;
  };
  usage: {
    article_generate_today: number;
    prompt_expand_today: number;
    image_generate_today: number;
    knowledge_total_bytes: number;
  };
  remaining: {
    article_generate_today: number;
    prompt_expand_today: number;
    image_generate_today: number;
    knowledge_total_bytes: number;
  };
};

export type AdminStats = {
  total_users: number;
  new_users_7d: number;
  total_paid_users: number;
  active_paid_users: number;
  active_trial_users: number;
  total_articles: number;
  articles_7d: number;
  total_knowledge_files: number;
  total_payments: number;
  paid_payments: number;
  paid_revenue_cents: number;
  paid_revenue_twd: number;
};

export type AdminRecentUser = {
  id: number;
  email: string;
  created_at: string;
};

export type AdminRecentPayment = {
  payment_id: number;
  user_id: number;
  user_email?: string;
  plan_code?: string;
  amount_cents: number;
  currency: string;
  provider: string;
  status: string;
  created_at: string;
};
