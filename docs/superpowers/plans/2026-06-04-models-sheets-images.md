# Models, Sheets, and Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update AI model choices, add multi-destination Google Sheets article export, and improve image generation with current models and social-platform sizes.

**Architecture:** Keep model catalog updates in settings API and frontend fallbacks. Add `google_sheet_destinations` as a per-user encrypted destination table with CRUD plus article export endpoints. Keep image provider settings but add social size presets and pass selected size from the article page to generation.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, httpx, cryptography/JWT signing via service-account JSON, Next.js, TypeScript, Tailwind.

---

### Task 1: Backend Model Catalog and Image Presets

**Files:**
- Modify: `backend/app/api/settings.py`
- Modify: `backend/app/models/settings.py`
- Modify: `backend/app/schemas/settings.py`
- Modify: `backend/app/api/images.py`
- Modify: `backend/app/schemas/image.py`
- Modify: `backend/app/services/image_service.py`
- Test: `backend/tests/test_catalog_and_images.py`

- [x] **Step 1: Write failing tests**
- [ ] **Step 2: Implement updated model catalog and image size catalog**
- [ ] **Step 3: Run tests and compile backend**

### Task 2: Google Sheets Destinations and Export

**Files:**
- Create: `backend/app/models/google_sheet_destination.py`
- Create: `backend/app/schemas/google_sheets.py`
- Create: `backend/app/services/google_sheets_service.py`
- Create: `backend/app/api/google_sheets.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/migrations.py`
- Test: `backend/tests/test_google_sheets.py`

- [x] **Step 1: Write failing tests**
- [ ] **Step 2: Implement encrypted multi-destination CRUD**
- [ ] **Step 3: Implement article export through Google Sheets append API**
- [ ] **Step 4: Run focused backend tests**

### Task 3: Frontend Settings and Article Workflow

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/settings/page.tsx`
- Modify: `frontend/app/articles/page.tsx`

- [ ] **Step 1: Expose new API types and client calls**
- [ ] **Step 2: Add Google Sheets destination management to settings**
- [ ] **Step 3: Add Sheets destination selector/export button and image size selector to articles**
- [ ] **Step 4: Run Next.js build**

### Task 4: Verification and Publish

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document Google Sheets service-account setup and model/image updates**
- [ ] **Step 2: Run backend tests, backend compile, and frontend build**
- [ ] **Step 3: Inspect git diff and commit intended files**
- [ ] **Step 4: Push branch to `kern0907-303/ai-article-saas`**
