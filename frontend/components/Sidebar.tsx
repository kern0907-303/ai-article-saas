"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { isAuthEnabled } from "@/lib/auth-config";
import { clearToken } from "@/lib/auth";

const navItems = [
  { href: "/settings", label: "系統設定" },
  { href: "/billing", label: "訂閱與付款" },
  { href: "/knowledge", label: "個人知識庫" },
  { href: "/articles", label: "文章創作與發布" },
  { href: "/published", label: "公開文章" },
  { href: "/admin", label: "後台儀表板" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const logout = () => {
    clearToken();
    router.replace("/login");
  };

  return (
    <aside className="w-full md:w-64 border-r border-[var(--line)] bg-[linear-gradient(180deg,rgba(255,251,240,0.96),rgba(255,226,163,0.82))] p-5 backdrop-blur-md">
      <span className="brand-pill">Pro 工作台</span>
      <h1 className="mt-2 text-xl font-bold text-[var(--text)]">AI 文章 SaaS</h1>
      <p className="mt-1 text-sm text-[var(--text-soft)]">設定、生成、發布一站完成</p>

      <nav className="mt-6 space-y-2">
        {navItems.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-lg px-3 py-2 text-sm font-medium transition ${
                active
                  ? "border border-[#f09a29] bg-[linear-gradient(135deg,#ffbe0b,#ff7b00)] text-white shadow-[0_10px_24px_rgba(255,123,0,0.22)]"
                  : "border border-transparent bg-white/65 text-[var(--text-soft)] hover:border-[#f3c56f] hover:bg-white/85"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {isAuthEnabled() ? (
        <button
          type="button"
          onClick={logout}
          className="mt-6 w-full rounded-lg border border-[#efb24e] bg-white/72 px-3 py-2 text-sm text-[var(--text)] transition hover:bg-white/90"
        >
          登出
        </button>
      ) : null}
    </aside>
  );
}
