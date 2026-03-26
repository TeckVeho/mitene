"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const userId = searchParams.get("user_id");
    const email = searchParams.get("email");
    const displayName = searchParams.get("display_name");

    if (userId && email && displayName) {
      if (typeof window !== "undefined") {
        localStorage.setItem("user_id", userId);
        localStorage.setItem("user_email", email);
        localStorage.setItem("user_display_name", displayName);
        window.dispatchEvent(new Event("mitene-auth-changed"));
      }
      router.replace("/");
    } else {
      router.replace("/login?error=invalid_callback");
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-white">
      <Loader2 className="size-10 animate-spin text-[#606060] dark:text-[#909090] mb-4" />
      <p className="text-sm text-[#606060] dark:text-[#909090]">ログイン中...</p>
    </div>
  );
}

export default function LoginCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex flex-col items-center justify-center bg-white dark:bg-[#0f0f0f]">
        <Loader2 className="size-10 animate-spin text-[#606060] dark:text-[#909090] mb-4" />
        <p className="text-sm text-[#606060] dark:text-[#909090]">ログイン中...</p>
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
