"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { PlaySquare, Github } from "lucide-react";
import { useLocale } from "@/lib/locale-context";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
const GITHUB_LOGIN_URL = `${API_BASE.replace(/\/api\/?$/, "")}/api/auth/github`;

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useLocale();
  const error = searchParams.get("error");

  function handleGitHubLogin() {
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const sep = GITHUB_LOGIN_URL.includes("?") ? "&" : "?";
    const url = `${GITHUB_LOGIN_URL}${sep}frontend_base=${encodeURIComponent(origin)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  // 別タブでログイン完了した場合、opener からポーリングで検知する
  useEffect(() => {
    const checkLoggedIn = () => {
      if (typeof window === "undefined") return;
      const userId = localStorage.getItem("user_id");
      if (userId) {
        router.push("/");
      }
    };
    const id = setInterval(checkLoggedIn, 500);
    return () => clearInterval(id);
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-[#0f0f0f] px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center gap-4 mb-8">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex items-center justify-center size-14 rounded-xl bg-[#ff0000] text-white">
              <PlaySquare className="size-8" />
            </div>
            <span className="text-2xl font-bold text-[#0f0f0f] dark:text-[#f1f1f1]">MITENE</span>
          </Link>
          <p className="text-sm text-[#606060] dark:text-[#909090]">{t.login.forEngineers}</p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-[#212121] border border-[#e5e5e5] dark:border-[#3f3f3f] rounded-2xl shadow-sm p-8 space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-[#0f0f0f] dark:text-[#f1f1f1]">{t.login.title}</h2>
            <p className="text-sm text-[#606060] dark:text-[#909090] mt-1">
              {t.login.subtitle}
            </p>
          </div>

          {error && (
            <div className="px-3 py-2.5 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">
                {error === "access_denied" ? t.login.authErrorCancelled : t.login.authError + ": " + error}
              </p>
            </div>
          )}

          <button
            onClick={handleGitHubLogin}
            className="w-full flex items-center justify-center gap-3 h-12 px-4 rounded-xl bg-[#0f0f0f] dark:bg-[#f1f1f1] text-white dark:text-[#0f0f0f] font-medium hover:bg-[#272727] dark:hover:bg-[#e5e5e5] transition-colors"
          >
            <Github className="size-5" />
            {t.login.loginWithGitHub}
          </button>

          <p className="text-xs text-[#606060] dark:text-[#909090] text-center">
            {t.login.authOpensInNewTab}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-white dark:bg-[#0f0f0f]">
        <div className="size-8 animate-spin rounded-full border-2 border-[#e5e5e5] dark:border-[#3f3f3f] border-t-[#ff0000]" />
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
