# AI 文章生成與自動發布 SaaS MVP

本專案為前後端分離的 Web App MVP，包含：
- 後端：FastAPI + SQLAlchemy + SQLite
- 前端：Next.js + Tailwind CSS（UI 全繁體中文）

目標功能：
- 系統設定（API Keys）
- 個人知識庫（上傳參考檔）
- AI 文章生成
- AI 配圖（依常見社群平台尺寸輸出）
- 寫好的文章上傳至多個 Google Sheets 目的地
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

### 5) Google Sheets 準備表
- `GET /google-sheets/destinations`：列出目前使用者的 Google Sheets 目的地
- `POST /google-sheets/destinations`：新增目的地（目的地名稱、Spreadsheet ID、工作表名稱、Service Account JSON）
- `PUT /google-sheets/destinations/{destination_id}`：更新目的地
- `DELETE /google-sheets/destinations/{destination_id}`：刪除目的地
- `POST /articles/{article_id}/export/google-sheets`：把目前文章追加到指定或預設 Google Sheet

每個使用者可建立多個目的地，用來對應不同客戶、品牌帳號或內容準備頁。Service Account JSON 會加密後存入資料庫。請到 Google Cloud 建立 Service Account，啟用 Google Sheets API，並把目標試算表分享給該 Service Account 的 `client_email`，至少授予編輯權限。

## Phase 3：前端 UI（Next.js）

具備側邊欄導覽：
- `系統設定`
- `個人知識庫`
- `文章創作與發布`

`文章創作與發布` 頁面包含三區塊：
1. 選擇參考檔案、輸入主題與大綱、點擊「生成文章」
2. 大型文字編輯區，可手動修改並儲存
3. 發布按鈕（Google Sheets / 個人網頁 / 社交平台）、AI 配圖尺寸選項與狀態顯示

目前模型選項已更新：
- OpenAI：GPT-5.5、GPT-5.4、GPT-5.4 mini/nano，圖片預設 GPT Image 2
- Anthropic：Claude Opus 4.8、Claude Sonnet 4.6、Claude Haiku 4.5
- Gemini：Gemini 3.5 Flash、Gemini 3.1 Pro、Gemini 3.1 Flash-Lite
- 圖片尺寸：Instagram 方形、Instagram Story/Reels、Facebook/LinkedIn 連結圖、X/Twitter 橫式圖、部落格封面

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
NEXT_PUBLIC_AUTH_ENABLED=false
```

建議改為：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001/api
NEXT_PUBLIC_AUTH_ENABLED=false
```

## 登入功能開關

目前登入功能預設關閉，但程式碼與登入頁保留。關閉時前端會隱藏登入、註冊、忘記密碼與登出入口，後端會使用一個本機預設帳號處理 API 請求，避免帳號資料庫不穩定造成網站不能用。

若未來要重新啟用登入：

```bash
# backend
AUTH_ENABLED=true

# frontend
NEXT_PUBLIC_AUTH_ENABLED=true
```

重新啟用前請先接好持久化資料庫，例如 PostgreSQL，避免帳號再次因部署或重啟消失。

## 生產環境資料持久化

如果你發現網站一更新、後端一重啟，會員帳號就像不存在，需要重新註冊，通常不是登入頁問題，而是後端資料庫沒有持久化。

目前後端設定邏輯如下：
- 若有 `DATABASE_URL`，會使用指定資料庫位置
- 若設定 `RENDER_DISK_PATH=/var/data`，預設會把 SQLite 放到 `/var/data/ai-article-saas/app.db`
- `STORAGE_DIR` 建議放在同一個 Persistent Disk，例如 `/var/data/ai-article-saas/storage`
- 在雲端平台若沒有 Persistent Disk 或外部資料庫，SQLite 檔案很容易在 redeploy 後消失

目前 Render Blueprint 採用「Persistent Disk + SQLite」方案，避免再新增外部資料庫服務。正式環境至少要設定以下後端環境變數：

```bash
RENDER_DISK_PATH=/var/data
DATABASE_URL=sqlite:////var/data/ai-article-saas/app.db
STORAGE_DIR=/var/data/ai-article-saas/storage
AUTH_ENABLED=false
JWT_SECRET_KEY=請填固定且夠長的隨機字串，不要重新產生
ENCRYPTION_SECRET=請填固定密鑰，不要重新產生，否則既有 API Key 會解不開
ADMIN_API_KEY=請填固定且夠長的管理金鑰
REQUIRE_PERSISTENT_DATABASE=true
CORS_ORIGINS=https://你的前端網域
```

後台已新增「帳號資料區」，可查看：
- 目前帳號資料是否使用持久化資料庫
- 註冊帳號列表
- 每個帳號的訂閱狀態、文章數、知識庫檔案數與付款筆數

`REQUIRE_PERSISTENT_DATABASE=true` 用於正式環境保護帳號資料。若後端沒有接上 PostgreSQL `DATABASE_URL` 或 Render Persistent Disk，後台會標示帳號資料不安全，服務仍會啟動，避免設定錯誤直接造成網站崩潰。

### Render 部署建議：Persistent Disk

本 repo 根目錄 `render.yaml` 會建立：
- 1 個 FastAPI backend 服務
- 1 個掛載在 `/var/data` 的 Persistent Disk
- 並把 backend 的 `DATABASE_URL` 固定到 `/var/data/ai-article-saas/app.db`
- 知識庫檔案、未來圖片檔會保存到 `/var/data/ai-article-saas/storage`

Render Persistent Disk 需要 paid web service，`render.yaml` 目前使用 `plan: starter` 與 `sizeGB: 1`。只有 disk mount path 底下的檔案會跨 deploy/restart 保存。

部署時只要：

1. 將 repo 連到 Render
2. 使用 Blueprint / `render.yaml`
3. 在 Render 後台填入固定的 `JWT_SECRET_KEY`、`ENCRYPTION_SECRET`、`ADMIN_API_KEY`
4. 把 `CORS_ORIGINS` 改成你的前端網址
5. 前端 `NEXT_PUBLIC_API_BASE_URL` 指向 Render backend，例如：

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com/api
```

如果舊環境已經有 Render Free Postgres，從 `render.yaml` 移除資料庫不會自動刪除既有資料庫。確認新版本已經改用 Persistent Disk 後，可在 Render Dashboard 手動刪除不用的 Postgres，避免混淆。

### 本機開發

可參考 `backend/.env.example` 建立 `backend/.env`：

```bash
cp backend/.env.example backend/.env
```

如果只是本機測試，不填 `DATABASE_URL` 也可以，系統會用 SQLite；
但如果要避免資料因環境更新消失，正式環境請改用 PostgreSQL。

## 補充：未來商業化擴充建議

- 導入 JWT / OAuth（取代 `x-user-id`）
- 新增租戶表（Tenant）與 Billing（訂閱/用量）
- SQLite 換 PostgreSQL（依 `user_id` 或 `tenant_id` 做資料隔離策略）
- 背景佇列（Celery/RQ）處理長文生成與發布重試
- API Key 加密儲存（KMS/Hashicorp Vault 或應用層加密）
