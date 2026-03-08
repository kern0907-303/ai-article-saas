"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { clearToken } from "@/lib/auth";

const navItems = [
  { href: "/settings", label: "系統設定" },
  { href: "/billing", label: "訂閱與付款" },
  { href: "/knowledge", label: "個人知識庫" },
  { href: "/articles", label: "文章創作與發布" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const logout = () => {
    clearToken();
    router.replace("/login");
  };

  return (
    <aside className="w-full md:w-64 bg-white/85 border-r border-[var(--line)] p-5 backdrop-blur-sm">
      <span className="brand-pill">Pro 工作台</span>
      <h1 className="text-xl font-bold text-[#0d7f7a] mt-2">AI 文章 SaaS</h1>
      <p className="text-sm text-slate-500 mt-1">設定、生成、發布一站完成</p>

      <nav className="mt-6 space-y-2">
        {navItems.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-lg px-3 py-2 text-sm font-medium transition ${
                active ? "bg-[#0abab5] text-white shadow-sm" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <button
        type="button"
        onClick={logout}
        className="mt-6 w-full rounded-lg border border-[#bde6e3] bg-[#f0fbfa] px-3 py-2 text-sm text-[#0d7f7a] hover:bg-[#e2f6f5]"
      >
        登出
      </button>
    </aside>
  );
}
