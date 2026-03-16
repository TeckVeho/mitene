"use client";

import { useLocale } from "@/lib/locale-context";
import { Globe } from "lucide-react";
import { useEffect, useState } from "react";

const LOCALE_LABELS: Record<"ja" | "vi", string> = {
  ja: "日本語",
  vi: "Tiếng Việt",
};

export function LanguageToggle() {
  const { locale, setLocale } = useLocale();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      const target = e.target as HTMLElement;
      if (!target.closest("[data-language-toggle]")) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  if (!mounted) {
    return (
      <div className="flex items-center justify-center size-10 rounded-full bg-[#f2f2f2] dark:bg-[#272727]" />
    );
  }

  return (
    <div className="relative" data-language-toggle>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-center size-10 rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
        aria-label={locale === "ja" ? "言語を切り替え（日本語/ベトナム語）" : "Chuyển ngôn ngữ (Tiếng Nhật/Tiếng Việt)"}
        title={LOCALE_LABELS[locale]}
      >
        <Globe className="size-5 text-[#0f0f0f] dark:text-[#f1f1f1]" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-44 bg-white dark:bg-[#212121] border border-[#e5e5e5] dark:border-[#3f3f3f] rounded-xl shadow-lg py-2 z-50">
          <button
            onClick={() => {
              setLocale("ja");
              setOpen(false);
            }}
            className={`
              w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left transition-colors
              ${locale === "ja"
                ? "bg-[#f2f2f2] dark:bg-[#272727] font-semibold text-[#0f0f0f] dark:text-[#f1f1f1]"
                : "text-[#0f0f0f] dark:text-[#f1f1f1] hover:bg-[#f2f2f2] dark:hover:bg-[#272727]"
              }
            `}
          >
            <span className="text-base">🇯🇵</span>
            {LOCALE_LABELS.ja}
          </button>
          <button
            onClick={() => {
              setLocale("vi");
              setOpen(false);
            }}
            className={`
              w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left transition-colors
              ${locale === "vi"
                ? "bg-[#f2f2f2] dark:bg-[#272727] font-semibold text-[#0f0f0f] dark:text-[#f1f1f1]"
                : "text-[#0f0f0f] dark:text-[#f1f1f1] hover:bg-[#f2f2f2] dark:hover:bg-[#272727]"
              }
            `}
          >
            <span className="text-base">🇻🇳</span>
            {LOCALE_LABELS.vi}
          </button>
        </div>
      )}
    </div>
  );
}
