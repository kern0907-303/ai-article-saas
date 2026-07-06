"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Entitlements, KnowledgeFile, Workspace } from "@/lib/types";

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

export default function KnowledgePage() {
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [includeAsDefaultReference, setIncludeAsDefaultReference] = useState(true);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("writing_skill");
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [status, setStatus] = useState("");

  const loadFiles = async () => {
    try {
      const entitlementData = await api.getEntitlements();
      setEntitlements(entitlementData);
      if (!entitlementData.is_active) {
        setFiles([]);
        return;
      }

      const [workspaceData, data] = await Promise.all([
        api.listWorkspaces(),
        api.listFiles({ workspace_id: selectedWorkspaceId || undefined }),
      ]);
      setWorkspaces(workspaceData);
      if (!selectedWorkspaceId) {
        setSelectedWorkspaceId(workspaceData.find((workspace) => workspace.is_default)?.id || workspaceData[0]?.id || null);
      }
      setFiles(data);
    } catch (err) {
      setStatus(`讀取失敗：${(err as Error).message}`);
    }
  };

  useEffect(() => {
    loadFiles();
  }, [selectedWorkspaceId]);

  const createWorkspace = async () => {
    if (!newWorkspaceName.trim()) {
      setStatus("請輸入品牌/專案名稱");
      return;
    }

    setStatus("建立品牌/專案中...");
    try {
      const created = await api.createWorkspace({
        name: newWorkspaceName.trim(),
        is_default: workspaces.length === 0,
      });
      setWorkspaces((prev) => [created, ...prev]);
      setSelectedWorkspaceId(created.id);
      setNewWorkspaceName("");
      setStatus("品牌/專案已建立");
    } catch (err) {
      setStatus(`建立失敗：${(err as Error).message}`);
    }
  };

  const onUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatus("上傳中...");
    try {
      await api.uploadFile(file, {
        includeAsDefaultReference,
        workspaceId: selectedWorkspaceId,
        category: selectedCategory,
      });
      setStatus("上傳成功");
      await loadFiles();
      e.target.value = "";
    } catch (err) {
      setStatus(`上傳失敗：${(err as Error).message}`);
    }
  };

  const onToggleDefaultReference = async (file: KnowledgeFile, checked: boolean) => {
    setStatus("更新參考設定中...");
    try {
      await api.updateFileDefaultReference(file.id, checked);
      setFiles((prev) =>
        prev.map((item) => (item.id === file.id ? { ...item, is_default_reference: checked } : item)),
      );
      setStatus("參考設定已更新");
    } catch (err) {
      setStatus(`更新失敗：${(err as Error).message}`);
    }
  };

  const onDelete = async (file: KnowledgeFile) => {
    const ok = window.confirm(`確定要刪除「${file.file_name}」嗎？此操作無法復原。`);
    if (!ok) return;

    setStatus("刪除中...");
    try {
      const result = await api.deleteFile(file.id);
      setStatus(result.message);
      await loadFiles();
    } catch (err) {
      setStatus(`刪除失敗：${(err as Error).message}`);
    }
  };

  const hasActiveAccess = !!entitlements?.is_active;
  const showAccessWarning = entitlements !== null && !entitlements.is_active;

  return (
    <section className="space-y-5 max-w-5xl">
      <div className="card-surface p-6 space-y-2">
        <span className="brand-pill">Knowledge Base</span>
        <h2 className="text-2xl font-bold">新增寫作資料</h2>
        <p className="text-slate-700">選品牌/專案、選資料類型、上傳檔案。AI 寫作時會依這些資料讀取，不會混到其他帳號。</p>
      </div>

      {showAccessWarning && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-5 text-amber-900">
          <p className="text-sm font-semibold">目前尚未開通可用方案</p>
          <p className="mt-1 text-sm">知識庫上傳需要先啟用 7 天試用或完成付款，避免按下去像沒反應。</p>
          <Link href="/billing" className="mt-3 inline-flex rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white">
            前往訂閱與付款
          </Link>
        </div>
      )}

      <div className="card-surface p-6 space-y-4">
        <div>
          <h3 className="text-lg font-semibold">上傳資料</h3>
          <p className="mt-1 text-sm text-slate-600">第一次使用只要完成這三步，之後到文章頁選同一個品牌/專案即可。</p>
        </div>

        <div className="grid md:grid-cols-2 gap-3">
          <label className="block text-sm font-medium text-slate-700">
            1. 品牌 / 專案
            <select
              className="mt-2 w-full rounded-lg border border-slate-300 p-2"
              value={selectedWorkspaceId || ""}
              onChange={(e) => setSelectedWorkspaceId(e.target.value ? Number(e.target.value) : null)}
              disabled={!hasActiveAccess}
            >
              <option value="">未指定品牌/專案</option>
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}{workspace.is_default ? "（預設）" : ""}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-medium text-slate-700">
            2. 資料類型
            <select
              className="mt-2 w-full rounded-lg border border-slate-300 p-2"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              disabled={!hasActiveAccess}
            >
              {KNOWLEDGE_CATEGORIES.map((category) => (
                <option key={category.key} value={category.key}>
                  {category.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="block text-sm font-medium text-slate-700">
          3. 選擇 Markdown/TXT 檔案
          <input
            type="file"
            accept=".md,.markdown,.txt,text/markdown,text/plain"
            className="mt-2 block w-full rounded-lg border border-slate-300 p-2 disabled:cursor-not-allowed disabled:opacity-60"
            onChange={onUpload}
            disabled={!hasActiveAccess}
          />
        </label>

        <details className="rounded-xl border border-[var(--line)] bg-white/60 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-[var(--text)]">進階：新增品牌/專案與預設參考</summary>
          <div className="mt-4 space-y-4">
            <label className="block text-sm font-medium text-slate-700">
              新增品牌/專案
              <div className="mt-2 flex gap-2">
                <input
                  className="w-full rounded-lg border border-slate-300 p-2"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  placeholder="例如：客戶 A、品牌 B、專案 C"
                  disabled={!hasActiveAccess}
                />
                <button
                  type="button"
                  className="brand-btn-secondary px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={createWorkspace}
                  disabled={!hasActiveAccess}
                >
                  新增
                </button>
              </div>
            </label>

            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={includeAsDefaultReference}
                onChange={(e) => setIncludeAsDefaultReference(e.target.checked)}
              />
              上傳後自動勾選為文章預設參考檔
            </label>
          </div>
        </details>

        <p className="text-xs text-slate-500">建議一個 skill 或一個主題放一檔；生成時會依目前品牌/專案和分類挑選相關段落。</p>
        {status && <p className="text-sm text-slate-600">{status}</p>}
      </div>

      <details className="card-surface p-6">
        <summary className="cursor-pointer text-lg font-semibold">
          已上傳資料 <span className="brand-pill ml-2">{files.length} 份</span>
        </summary>

        {files.length === 0 ? (
          <p className="mt-4 text-slate-500">目前尚無檔案，先上傳 1-2 份資料再去文章頁測試會更有感。</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {files.map((file) => (
              <li key={file.id} className="rounded-xl border border-[var(--line)] bg-[#fbfefe] p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="font-semibold text-slate-800 break-all">{file.file_name}</p>
                  <button
                    className="brand-btn-danger px-3 py-2 text-sm font-semibold whitespace-nowrap"
                    onClick={() => onDelete(file)}
                  >
                    刪除檔案
                  </button>
                </div>
                <p className="text-sm text-slate-500 mt-1">
                  大小：{file.file_size} bytes / 分類：{KNOWLEDGE_CATEGORIES.find((item) => item.key === file.category)?.label || file.category} / 預設寫作參考：{file.is_default_reference ? "是" : "否"}
                </p>
                <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={file.is_default_reference}
                    onChange={(e) => onToggleDefaultReference(file, e.target.checked)}
                  />
                  每次生成文章預設參考此檔案
                </label>
                <p className="text-sm text-slate-700 mt-2">預覽：{file.extracted_text_preview || "（無）"}</p>
              </li>
            ))}
          </ul>
        )}
      </details>
    </section>
  );
}
