"use client";

import { useEffect, useMemo, useState } from "react";

import { listPublishedArticlesWithFallback } from "@/lib/api";
import type { PublicArticle, PublishedArticleSource } from "@/lib/types";

function getRuntimeFilters() {
  if (typeof window === "undefined") return {};
  const params = new URL(window.location.href).searchParams;
  return {
    ownerId: params.get("owner_id") || undefined,
    workspaceId: params.get("workspace_id") || undefined,
  };
}

function sourceLabel(source: PublishedArticleSource) {
  return source === "database" ? "正式資料庫" : "GitHub JSON 備援";
}

export default function PublishedArticlesPage() {
  const [articles, setArticles] = useState<PublicArticle[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [source, setSource] = useState<PublishedArticleSource>("database");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    listPublishedArticlesWithFallback(getRuntimeFilters())
      .then((result) => {
        if (!mounted) return;
        setArticles(result.articles);
        setSelectedId(result.articles[0]?.id ?? null);
        setSource(result.source);
        setNotice(result.error ? `無法連線正式資料庫，已改讀備援資料：${result.error}` : "");
      })
      .catch((err) => {
        if (!mounted) return;
        setNotice((err as Error).message);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const selectedArticle = useMemo(
    () => articles.find((article) => article.id === selectedId) || articles[0] || null,
    [articles, selectedId],
  );

  return (
    <section className="mx-auto max-w-6xl space-y-5">
      <header className="space-y-3 border-b border-[var(--line)] pb-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <span className="brand-pill">Published</span>
            <h1 className="mt-2 text-3xl font-bold text-[var(--text)]">公開文章</h1>
          </div>
          <span className="rounded-lg border border-[var(--line)] bg-white/70 px-3 py-2 text-sm text-[var(--text-soft)]">
            資料來源：{sourceLabel(source)}
          </span>
        </div>
        {notice ? <p className="text-sm text-amber-800">{notice}</p> : null}
      </header>

      {loading ? (
        <div className="rounded-lg border border-[var(--line)] bg-white/72 p-5 text-sm text-[var(--text-soft)]">載入公開文章中...</div>
      ) : articles.length === 0 ? (
        <div className="rounded-lg border border-[var(--line)] bg-white/72 p-5">
          <h2 className="text-lg font-semibold">目前沒有公開文章</h2>
          <p className="mt-2 text-sm text-[var(--text-soft)]">
            當文章在後台按下發布後，正式資料庫會顯示在這裡；若資料庫暫時無法連線，頁面會讀取 GitHub JSON 備援檔。
          </p>
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
          <aside className="space-y-2">
            {articles.map((article) => (
              <button
                key={article.id}
                type="button"
                onClick={() => setSelectedId(article.id)}
                className={`w-full rounded-lg border px-4 py-3 text-left transition ${
                  selectedArticle?.id === article.id
                    ? "border-[#ef9a2f] bg-white text-[var(--text)] shadow-[0_10px_22px_rgba(176,94,6,0.14)]"
                    : "border-[var(--line)] bg-white/68 text-[var(--text-soft)] hover:bg-white"
                }`}
              >
                <span className="block text-sm font-semibold">{article.topic}</span>
                <span className="mt-1 block line-clamp-2 text-xs">{article.outline}</span>
              </button>
            ))}
          </aside>

          {selectedArticle ? (
            <article className="rounded-lg border border-[var(--line)] bg-white/78 p-5">
              <p className="text-xs text-[var(--text-soft)]">
                更新時間：{new Date(selectedArticle.updated_at).toLocaleDateString("zh-TW")}
              </p>
              <h2 className="mt-2 text-2xl font-bold text-[var(--text)]">{selectedArticle.topic}</h2>
              <p className="mt-3 border-l-4 border-[#ef9a2f] pl-3 text-sm text-[var(--text-soft)]">{selectedArticle.outline}</p>
              <div className="mt-5 whitespace-pre-wrap text-base leading-8 text-[#3f2a18]">{selectedArticle.content}</div>
            </article>
          ) : null}
        </div>
      )}
    </section>
  );
}
