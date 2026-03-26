"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import Sidebar from "@/components/Sidebar";
import { getToken } from "@/lib/auth";

const PUBLIC_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password"];

export default function AuthShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);

  const isPublicRoute = useMemo(() => PUBLIC_ROUTES.includes(pathname), [pathname]);

  useEffect(() => {
    setHydrated(true);
    setToken(getToken());
  }, [pathname]);

  useEffect(() => {
    if (!hydrated) return;

    if (!token && !isPublicRoute) {
      setRedirecting(true);
      router.replace("/login");
      return;
    }

    if (token && isPublicRoute) {
      setRedirecting(true);
      router.replace("/settings");
      return;
    }

    setRedirecting(false);
  }, [hydrated, token, isPublicRoute, router]);

  if (!hydrated || redirecting) {
    return <div className="flex min-h-screen items-center justify-center text-[var(--text-soft)]">載入中...</div>;
  }

  if (isPublicRoute) {
    return <main className="min-h-screen p-4 md:p-8"><div className="mx-auto max-w-6xl">{children}</div></main>;
  }

  return (
    <div className="min-h-screen md:flex">
      <Sidebar />
      <main className="flex-1 p-4 md:p-8">{children}</main>
    </div>
  );
}
