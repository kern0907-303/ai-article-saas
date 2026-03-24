"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Entitlements, KnowledgeFile } from "@/lib/types";

export default function KnowledgePage() {
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [includeAsDefaultReference, setIncludeAsDefaultReference] = useState(true);
  const [status, setStatus] = useState("");

  const loadFiles = async () => {
    try {
      const entitlementData = await api.getEntitlements();
      setEntitlements(entitlementData);
      if (!entitlementData.is_active) {
        setFiles([]);
        return;
      }

      const data = await api.listFiles();
      setFiles(data);
    } catch (err) {
      setStatus(`讀取失敗：${(err as Error).message}`);
    }
  };

  useEffect(() => {
    loadFiles();
  }, []);

  const onUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatus("上傳中...");
    try {
      await api.uploadFile(file, includeAsDefaultReference);
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
        <h2 className="text-2xl font-bold">個人知識庫</h2>
        <p className="text-slate-700">上傳 TXT 等參考檔作為 AI 生成依據。建議先放品牌資料、產品說明、常見 QA。</p>
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

      <div className="card-surface p-6 space-y-3">
        <h3 className="text-lg font-semibold">上傳檔案</h3>
        <label className="block text-sm font-medium text-slate-700">
          選擇檔案
          <input
            type="file"
            className="mt-2 block w-full rounded-lg border border-slate-300 p-2 disabled:cursor-not-allowed disabled:opacity-60"
            onChange={onUpload}
            disabled={!hasActiveAccess}
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={includeAsDefaultReference}
            onChange={(e) => setIncludeAsDefaultReference(e.target.checked)}
          />
          上傳後自動勾選為「文章預設參考檔」
        </label>
        <p className="text-xs text-slate-500">建議單檔內容主題一致，讓生成時的上下文更精準。</p>
        {status && <p className="text-sm text-slate-600">{status}</p>}
      </div>

      <div className="card-surface p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">已上傳檔案</h3>
          <span className="brand-pill">{files.length} 份資料</span>
        </div>

        {files.length === 0 ? (
          <p className="text-slate-500">目前尚無檔案，先上傳 1-2 份資料再去文章頁測試會更有感。</p>
        ) : (
          <ul className="space-y-3">
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
                <p className="text-sm text-slate-500 mt-1">大小：{file.file_size} bytes</p>
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
      </div>
    </section>
  );
}
