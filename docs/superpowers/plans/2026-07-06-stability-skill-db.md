# Stability And Skill Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Cloudflare/Render deployment reproducible, make uploaded skill Markdown files reliably available to article generation, and add verification scripts that prove the site is stable before release.

**Architecture:** Keep uploaded files in the existing `knowledge_files` table and storage directory, but introduce a focused knowledge context service that selects default files, chunks Markdown/text, ranks chunks against the writing request, and enforces a character budget before prompt injection. Cloudflare Pages will build a static Next export and ship a `_worker.js` proxy so `/api/*` routes consistently reach Render, including health/readiness checks. Verification is scriptable from repo root.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite/Persistent Disk, pytest, Next.js static export, Cloudflare Pages Worker, shell scripts.

---

### Task 1: Add Knowledge Context Selection

**Files:**
- Create: `backend/app/services/knowledge_context_service.py`
- Create: `backend/tests/test_knowledge_context_service.py`
- Modify: `backend/app/api/articles.py`
- Modify: `backend/app/schemas/article.py`
- Modify: `backend/tests/test_ai_service.py`

- [ ] **Step 1: Write failing tests**

Create tests covering default reference selection, Markdown chunk ranking, and budget enforcement.

Run: `cd backend && python -m pytest tests/test_knowledge_context_service.py -q`

Expected: FAIL because `app.services.knowledge_context_service` does not exist.

- [ ] **Step 2: Implement `knowledge_context_service`**

Add functions:
- `split_knowledge_text(file_name, text, max_chunk_chars=2200) -> list[KnowledgeChunk]`
- `rank_knowledge_chunks(chunks, query, max_chars=24000) -> list[str]`
- `build_generation_contexts(db, user_id, selected_file_ids, topic, outline, user_prompt, use_default_references=True) -> tuple[list[str], list[int]]`

Implementation rules:
- If selected IDs are present, use those active files only.
- If no selected IDs are present and default references are enabled, use active `is_default_reference` files.
- Split Markdown at headings and keep YAML frontmatter near the top.
- Score chunks by query term overlap from topic, outline, and prompt.
- Cap injected context with a hard character budget.

- [ ] **Step 3: Wire article generation to the service**

Update `ArticleGenerateRequest` to include `use_default_references: bool = True`.

Update `articles.py` background generation to call `build_generation_contexts(...)`, pass returned contexts to `generate_article_with_provider`, and persist the actual `used_file_ids` CSV.

- [ ] **Step 4: Verify backend tests**

Run: `cd backend && python -m pytest tests/test_knowledge_context_service.py tests/test_ai_service.py -q`

Expected: PASS.

---

### Task 2: Make Cloudflare Pages Deployment Reproducible

**Files:**
- Modify: `frontend/next.config.ts`
- Modify: `frontend/package.json`
- Add: `frontend/public/_worker.js`
- Add: `frontend/public/_headers`
- Modify: `README.md`

- [ ] **Step 1: Add static export build path**

Set `output: "export"` in `next.config.ts` and add `build:cloudflare` script that runs `next build`.

- [ ] **Step 2: Add Cloudflare worker proxy**

Create `frontend/public/_worker.js` with:
- `API_ORIGIN` env fallback to `https://ai-article-saas.onrender.com`
- `/api/healthz` proxy to `${origin}/healthz`
- `/api/readyz` proxy to `${origin}/readyz`
- other `/api/*` proxy to `${origin}/api/*`
- CORS preflight handling for the Pages domain

- [ ] **Step 3: Add Cloudflare headers**

Create `frontend/public/_headers` with basic security headers for static assets.

- [ ] **Step 4: Verify static export**

Run: `npm --prefix frontend run build:cloudflare`

Expected: PASS and `frontend/out/_worker.js` exists.

---

### Task 3: Add Stability Verification Scripts

**Files:**
- Add: `backend/requirements-dev.txt`
- Add: `scripts/test_backend.sh`
- Add: `scripts/test_frontend.sh`
- Modify: `scripts/stability_check.sh`
- Modify: `frontend/package.json`

- [ ] **Step 1: Add backend test dependency file**

Create `backend/requirements-dev.txt` containing:

```txt
-r requirements.txt
pytest==8.4.2
```

- [ ] **Step 2: Add backend test script**

Create `scripts/test_backend.sh` that runs tests from `backend/` so imports resolve:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/backend"
python -m pytest tests -q
```

- [ ] **Step 3: Add frontend verification script**

Create `scripts/test_frontend.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
npm --prefix "$ROOT_DIR/frontend" run build:cloudflare
```

- [ ] **Step 4: Fix non-interactive lint/check**

Replace the frontend `lint` script with a non-interactive command that delegates to `build:cloudflare`, and add a `check` script with the same command.

- [ ] **Step 5: Upgrade stability check**

Make `scripts/stability_check.sh` accept:
- `FRONTEND_URL`, default `https://ai-article-saas.pages.dev`
- `BACKEND_URL`, default `https://ai-article-saas.onrender.com`

Check:
- frontend returns HTTP 200
- frontend `/api/knowledge-files` returns a non-5xx status
- backend `/healthz` returns HTTP 200
- backend `/readyz` returns HTTP 200
- warn if `/healthz` reports `persistent_storage_enabled: false`

---

### Task 4: Improve Knowledge UI Copy For Skill Markdown

**Files:**
- Modify: `frontend/app/knowledge/page.tsx`
- Modify: `frontend/app/articles/page.tsx`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Clarify upload affordance**

Update the knowledge page to say Markdown/TXT skill files are supported, set the file input accept list to `.md,.markdown,.txt,text/markdown,text/plain`, and show whether each file is a default writing reference.

- [ ] **Step 2: Send default reference intent from frontend**

Update `api.generateArticle` and article page payload to include `use_default_references: true`.

- [ ] **Step 3: Add selected reference status**

On the article page, show selected reference count and a clear empty state when no knowledge files exist.

---

### Task 5: Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run backend tests**

Run: `./scripts/test_backend.sh`

Expected: `36 passed` or higher.

- [ ] **Step 2: Run frontend build/export**

Run: `./scripts/test_frontend.sh`

Expected: PASS and static export generated.

- [ ] **Step 3: Run stability check**

Run: `./scripts/stability_check.sh`

Expected: HTTP checks complete; if production Render is still not persistent, script prints an explicit warning.

