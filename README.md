# AI 文章生成與自動發布 SaaS MVP

本專案為前後端分離的 Web App MVP，包含：
- 後端：FastAPI + SQLAlchemy + SQLite
- 前端：Next.js + Tailwind CSS（UI 全繁體中文）

目標功能：
- 系統設定（API Keys）
- 個人知識庫（上傳參考檔）
- AI 文章生成
- 模擬自動發布至個人網頁/社交平台

## 專案結構

```txt
AI-Article-SaaS/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  │  ├─ settings.py
│  │  │  ├─ knowledge_files.py
│  │  │  ├─ articles.py
│  │  │  └─ publish.py
│  │  ├─ core/
│  │  │  ├─ config.py
│  │  │  └─ database.py
│  │  ├─ models/
│  │  │  ├─ settings.py
│  │  │  ├─ knowledge_file.py
│  │  │  └─ article.py
│  │  ├─ schemas/
│  │  │  ├─ settings.py
│  │  │  ├─ knowledge_file.py
│  │  │  └─ article.py
│  │  ├─ services/
│  │  │  ├─ file_service.py
│  │  │  └─ ai_service.py
│  │  ├─ utils/
│  │  │  └─ deps.py
│  │  └─ main.py
│  ├─ storage/
│  └─ requirements.txt
├─ frontend/
│  ├─ app/
│  │  ├─ settings/page.tsx
│  │  ├─ knowledge/page.tsx
│  │  ├─ articles/page.tsx
│  │  ├─ layout.tsx
│  │  ├─ page.tsx
│  │  └─ globals.css
│  ├─ components/Sidebar.tsx
│  ├─ lib/
│  │  ├─ api.ts
│  │  └─ types.ts
│  ├─ package.json
│  ├─ tsconfig.json
│  ├─ next.config.ts
│  └─ postcss.config.mjs
└─ README.md
```

## Phase 1：系統架構與資料庫設計

### 架構設計
- 前端 Next.js 透過 REST API 呼叫 FastAPI。
- 後端以 `x-user-id` Header 模擬使用者識別（MVP）。
- 檔案上傳後存放在 `backend/storage/{user_id}/`。
- 所有核心資料表皆包含 `user_id`，預留未來多租戶（可轉 PostgreSQL + 真實 Tenant/Auth）。

### 資料表

1. `settings`
- `id`（PK）
- `user_id`（Unique）
- `openai_api_key`
- `website_api_key`
- `social_api_key`
- `website_endpoint`
- `social_endpoint`
- `notes`
- `created_at` / `updated_at`

2. `knowledge_files`
- `id`（PK）
- `user_id`（Index）
- `file_name`
- `stored_path`（Unique）
- `content_type`
- `file_size`
- `extracted_text_preview`
- `is_active`
- `created_at` / `updated_at`

3. `articles`
- `id`（PK）
- `user_id`（Index）
- `topic`
- `outline`
- `content`
- `selected_file_ids`（CSV）
- `generation_model`
- `generation_status`
- `published_to_website`
- `published_to_social`
- `publish_website_result`
- `publish_social_result`
- `created_at` / `updated_at`

## Phase 2：後端 API（FastAPI）

Base URL：`http://localhost:8000/api`

### 1) 設定模組
- `GET /settings`：讀取目前使用者設定
- `PUT /settings`：儲存/更新 API Keys 與 Endpoint

### 2) 檔案知識庫模組
- `POST /knowledge-files`：上傳檔案
- `GET /knowledge-files`：列出已上傳檔案
- `GET /knowledge-files/{file_id}/text`：讀取檔案全文

### 3) AI 生成模組
- `POST /articles/generate`：輸入主題、大綱、參考檔案 ID，讀取檔案內容作為 Context，呼叫 OpenAI 生成文章
- `GET /articles`：取得文章列表
- `GET /articles/{article_id}`：取得單篇文章
- `PUT /articles/{article_id}`：手動編輯後儲存

### 4) 發布模組（模擬）
- `POST /publish/website/{article_id}`
- `POST /publish/social/{article_id}`

目前先回傳模擬成功訊息，並更新文章發布狀態欄位。

## Phase 3：前端 UI（Next.js）

具備側邊欄導覽：
- `系統設定`
- `個人知識庫`
- `文章創作與發布`

`文章創作與發布` 頁面包含三區塊：
1. 選擇參考檔案、輸入主題與大綱、點擊「生成文章」
2. 大型文字編輯區，可手動修改並儲存
3. 發布按鈕（個人網頁 / 社交平台）與狀態顯示

## 本機啟動方式（穩定模式）

## 0. 先清理快取與汙染檔（建議每次改版後執行）

```bash
cd /Volumes/2T/AI-Article-SaaS
./scripts/clean_artifacts.sh
```

## 1. 啟動後端（8001）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

啟動後可開啟：
- Swagger: `http://127.0.0.1:8001/docs`
- Health: `http://127.0.0.1:8001/healthz`

## 2. 啟動前端（3001）

另開一個終端機：

```bash
cd frontend
npm install
npm run dev -- -p 3001
```

開啟：
- `http://localhost:3001`

注意：

```txt
請不要在 dev server 執行中同時跑 `npm run build`，兩者都會寫入 `.next`，會導致模組缺檔與頁面 500。
```

## 環境變數（前端）

可選，在 `frontend/.env.local`：

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_DEMO_USER_ID=demo-user
```

建議改為：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001/api
```

## 補充：未來商業化擴充建議

- 導入 JWT / OAuth（取代 `x-user-id`）
- 新增租戶表（Tenant）與 Billing（訂閱/用量）
- SQLite 換 PostgreSQL（依 `user_id` 或 `tenant_id` 做資料隔離策略）
- 背景佇列（Celery/RQ）處理長文生成與發布重試
- API Key 加密儲存（KMS/Hashicorp Vault 或應用層加密）
