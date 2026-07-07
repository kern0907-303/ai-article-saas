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

若個人網頁 Endpoint / API Key 都留空，`POST /publish/website/{article_id}` 會直接把文章標記為本系統公開文章，供公開文章頁與備援 JSON 使用。若兩者都有填，系統會先推送到外部網站 API，再標記為公開文章。

公開文章讀取：
- `GET /public/articles?owner_id={使用者ID}`：讀取指定帳號已發布到網站的文章
- `GET /public/articles?owner_id={使用者ID}&workspace_id={品牌/專案ID}`：只讀指定品牌/專案的公開文章

公開 API 不會輸出 `user_id`、參考檔案 ID、知識庫分類、AI 模型或其他私有生成欄位。

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
- OpenAI：GPT-5.5、GPT-5.4、GPT-5.4 mini/nano，圖片預設 GPT Image 1.5
- Anthropic：Claude Opus 4.8、Claude Sonnet 4.6、Claude Haiku 4.5
- Gemini：Gemini 3.5 Flash、Gemini 3.1 Pro、Gemini 3.1 Flash-Lite
- 圖片尺寸：Instagram 方形、Instagram Story/Reels、Facebook/LinkedIn 連結圖、X/Twitter 橫式圖、部落格封面

圖片生成流程：
- OpenAI GPT Image 模型會使用 `output_format`，不再傳舊版 `response_format`
- 生成後若已設定 pCloud，系統會把圖片上傳到指定 pCloud 資料夾
- 資料庫中的 `image_url` 會保存 pCloud 連結，而不是暫存的 base64 圖片資料
- 上傳 Google Sheets 時，系統會把該文章已生成圖片連結寫到第 K 欄

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

正式多人 SaaS 必須啟用登入。若 `AUTH_ENABLED=false`，後端會使用同一個本機預設帳號，所有使用者會共用同一份設定、文章與知識庫，不適合公開服務。重新啟用前請先接好持久化資料庫，避免帳號再次因部署或重啟消失。

## 生產環境資料持久化

如果你發現網站一更新、後端一重啟，會員帳號就像不存在，需要重新註冊，通常不是登入頁問題，而是後端資料庫沒有持久化。

目前後端設定邏輯如下：
- 若有 `DATABASE_URL`，會使用指定資料庫位置
- 若沒有 `DATABASE_URL`，會退回 SQLite 檔案
- 在 Render Free 上，SQLite 檔案與上傳檔案會因 redeploy/restart 消失
- 知識庫 Markdown 內容會存進資料庫欄位，免費部署時不依賴 Render Disk

### 免費部署建議：Render Free + 免費 Postgres

Render Free 不支援 Persistent Disk。免費方案請用外部免費 Postgres，例如 Supabase Free 或 Neon Free。Supabase 官方 Free plan 目前提供 500 MB database size 與 1 GB file storage；Neon 官方 Free plan 目前提供 $0、無時間限制、0.5 GB storage。這些額度足夠先做 MVP 與小規模測試。

正式環境至少要設定以下後端環境變數：

```bash
DATABASE_URL=postgresql://你的免費Postgres連線字串
AUTH_ENABLED=true
JWT_SECRET_KEY=請填固定且夠長的隨機字串，不要重新產生
ENCRYPTION_SECRET=請填固定密鑰，不要重新產生，否則既有 API Key 會解不開
ADMIN_API_KEY=請填固定且夠長的管理金鑰
REQUIRE_PERSISTENT_DATABASE=true
CORS_ORIGINS=https://你的前端網域
```

只有單人本機內測時才可暫時關閉：

```bash
AUTH_ENABLED=false
```

多人正式環境的 Cloudflare Pages 前端也要設定：

```bash
NEXT_PUBLIC_AUTH_ENABLED=true
```

否則前端會隱藏登入入口，而後端若要求 Token 會回 401。

後台已新增「帳號資料區」，可查看：
- 目前帳號資料是否使用持久化資料庫
- 註冊帳號列表
- 每個帳號的訂閱狀態、文章數、知識庫檔案數與付款筆數

`REQUIRE_PERSISTENT_DATABASE=true` 用於正式環境保護帳號資料。若後端沒有接上 PostgreSQL `DATABASE_URL`，後台會標示帳號資料不安全，服務仍會啟動，避免設定錯誤直接造成網站崩潰。

### Render 部署建議：Free Web Service

本 repo 根目錄 `render.yaml` 會建立 1 個 FastAPI backend 服務，使用 Render Free Web Service。資料持久化交給外部 Postgres，不使用 Render Disk。

部署時只要：

1. 將 repo 連到 Render
2. 使用 Blueprint / `render.yaml`
3. 在 Render 後台填入外部 Postgres 的 `DATABASE_URL`
4. 在 Render 後台填入固定的 `JWT_SECRET_KEY`、`ENCRYPTION_SECRET`、`ADMIN_API_KEY`
5. 把 `CORS_ORIGINS` 改成你的前端網址
6. 前端 `NEXT_PUBLIC_API_BASE_URL` 指向 Render backend，例如：

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com/api
```

如果舊環境已經有 Render Free Postgres 或其他 Postgres，確認資料已搬到新的 `DATABASE_URL` 後，再刪除不用的舊資料庫，避免混淆。

### Cloudflare Pages 部署建議：Static Export + Worker Proxy

前端可用 Next.js static export 部署到 Cloudflare Pages：

```bash
cd frontend
npm ci
npm run build:cloudflare
```

Cloudflare Pages 設定：

```txt
Build command: npm run build:cloudflare
Build output directory: out
Root directory: frontend
```

`frontend/public/_worker.js` 會在 export 後出現在 `out/_worker.js`，負責把同網域 `/api/*` 代理到 Render backend。預設後端為：

```txt
https://ai-article-saas.onrender.com
```

若要改後端，請在 Cloudflare Pages 環境變數設定：

```bash
API_ORIGIN=https://你的-render-backend.onrender.com
NEXT_PUBLIC_AUTH_ENABLED=true
```

特殊健康檢查路由：
- `https://你的-pages-網域/api/healthz` → Render `/healthz`
- `https://你的-pages-網域/api/readyz` → Render `/readyz`
- 其他 `/api/*` → Render `/api/*`

公開文章頁：
- `https://你的-pages-網域/published`
- 正式資料來源：Render backend `/api/public/articles`
- 備援資料來源：GitHub 內的 `frontend/public/published-articles.json`

Cloudflare Pages 需要新增以下環境變數，公開文章頁才知道要讀哪個帳號，不會把不同帳號的文章混在一起：

```bash
NEXT_PUBLIC_PUBLIC_ARTICLE_OWNER_ID=你的使用者ID
# 可選，只顯示某一個品牌/專案：
NEXT_PUBLIC_PUBLIC_ARTICLE_WORKSPACE_ID=你的品牌或專案ID
```

若不想用環境變數，也可以用網址指定：

```txt
https://你的-pages-網域/published?owner_id=你的使用者ID
https://你的-pages-網域/published?owner_id=你的使用者ID&workspace_id=你的品牌或專案ID
```

匯出 GitHub JSON 備援檔：

```bash
python3 scripts/export_public_articles.py --owner-id 你的使用者ID
# 只匯出某品牌/專案：
python3 scripts/export_public_articles.py --owner-id 你的使用者ID --workspace-id 你的品牌或專案ID
```

這個指令只會匯出已按「發布至個人網頁」且有內容的公開文章，不會匯出知識庫、API Key、未發布草稿或其他帳號資料。

正式部署後請跑：

```bash
./scripts/stability_check.sh
```

如果出現 `persistent_storage_enabled=false` 警告，代表 Render 後端沒有用到 Persistent Disk 或環境變數未套用，知識庫與設定仍有遺失風險。
如果出現 `auth_enabled=false` 警告，代表正式站仍在共用 fallback local user，會造成多人資料污染；公開服務前必須修正。

### 本機驗證指令

後端測試：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cd ..
./scripts/test_backend.sh
```

前端 static export：

```bash
./scripts/test_frontend.sh
```

### pCloud 圖片上傳設定

若要讓生成圖片自動上傳到 pCloud，請在 Render backend 設定：

```bash
PCLOUD_AUTH_TOKEN=你的 pCloud auth token
PCLOUD_API_HOST=api.pcloud.com
PCLOUD_FOLDER_ID=你的目標資料夾 ID
# 或使用資料夾路徑，二選一：
PCLOUD_FOLDER_PATH=/AI Article Images
PCLOUD_CREATE_PUBLIC_LINK=true
PCLOUD_USE_DIRECT_DOWNLOAD_LINK=true
```

pCloud 有 US 與 EU 兩個 API host。美國帳號通常用 `api.pcloud.com`，歐洲帳號通常用 `eapi.pcloud.com`。  
如果你提供的是 pCloud 資料夾路徑，請填 `PCLOUD_FOLDER_PATH`；如果能取得資料夾 ID，優先填 `PCLOUD_FOLDER_ID`。

若後端是跑在可存取 pCloud Drive 的本機或伺服器，也可以直接存到 pCloud Drive Public Folder：

```bash
PCLOUD_PUBLIC_FOLDER_PATH=/Users/erickair/pCloud Drive/Public Folder/article
PCLOUD_PUBLIC_BASE_URL=https://你的-pCloud-Public-Folder-直接連結/article
```

`PCLOUD_PUBLIC_FOLDER_PATH` 負責存檔，`PCLOUD_PUBLIC_BASE_URL` 負責組成可貼到 Google Sheets 的圖片網址。若未設定 `PCLOUD_PUBLIC_BASE_URL`，系統會先保存本機檔案路徑，但 Google Sheets 裡的連結不一定能在其他裝置開啟。

### 從舊資料庫搬到 Persistent Disk

如果已經在舊 Render Postgres 設定過 API Keys 或 Google Sheets 目的地，先不要刪舊資料庫。請在 Render Shell 或一次性 Job 執行：

```bash
cd backend
python scripts/migrate_database_to_disk.py \
  --source-url "$OLD_DATABASE_URL" \
  --target-url "sqlite:////var/data/ai-article-saas/app.db" \
  --remap-to-local-user
```

其中 `OLD_DATABASE_URL` 是舊 Render Postgres 的 external connection string。  
`--remap-to-local-user` 會把舊帳號底下的 `settings`、`google_sheet_destinations`、`articles` 等資料搬到目前登入關閉模式使用的本機預設帳號，讓網站立刻看得到。

如果新的 Persistent Disk SQLite 已經有錯誤或測試資料，而且確認不要保留，可加：

```bash
--replace-target
```

搬移工具只複製資料列，不會解密或重寫 API Key / Google Sheets Service Account JSON。只要 `ENCRYPTION_SECRET` 維持跟舊設定時相同，搬過去後就能正常解密使用。

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
