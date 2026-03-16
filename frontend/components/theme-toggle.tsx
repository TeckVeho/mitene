"use client";

import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { useLocale } from "@/lib/locale-context";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const { t } = useLocale();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="flex items-center justify-center size-10 rounded-full bg-[#f2f2f2] dark:bg-[#272727]" />
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="flex items-center justify-center size-10 rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
      aria-label={isDark ? t.theme.lightMode : t.theme.darkMode}
    >
      <Sun className="size-5 text-[#0f0f0f] dark:hidden" />
      <Moon className="size-5 text-[#f1f1f1] hidden dark:block" />
    </button>
  );
}
