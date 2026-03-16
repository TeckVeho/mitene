"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Search,
  Mic,
  Bell,
  RefreshCw,
  Menu,
  User,
  LogOut,
  History,
  Settings,
  X,
  PlaySquare,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useSidebar } from "./layout-client";
import { useLocale } from "@/lib/locale-context";
import type { User as UserType } from "@/lib/types";

function UserMenu() {
  const { t } = useLocale();
  const [user, setUser] = useState<UserType | null>(null);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    api.getCurrentUser().then((u) => setUser(u));
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleLogout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("user_id");
      localStorage.removeItem("user_email");
      localStorage.removeItem("user_display_name");
    }
    setUser(null);
    setOpen(false);
    router.push("/login");
  }

  if (!user) {
    return (
      <Link
        href="/login"
        className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#065fd4] text-[#065fd4] text-sm font-medium hover:bg-[#065fd4]/10 dark:border-[#3ea6ff] dark:text-[#3ea6ff] dark:hover:bg-[#3ea6ff]/10 transition-colors"
      >
        <User className="size-4" />
        <span>{t.common.login}</span>
      </Link>
    );
  }

  const initials = user.displayName
    .split(/\s+/)
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-center size-8 rounded-full bg-[#065fd4] text-white text-xs font-bold hover:ring-2 hover:ring-[#065fd4]/30 transition-all"
        aria-label={t.header.accountMenu}
      >
        {initials}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-60 bg-white dark:bg-[#212121] border border-[#e5e5e5] dark:border-[#3f3f3f] rounded-xl shadow-lg py-2 z-50">
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[#e5e5e5] dark:border-[#3f3f3f]">
            <div className="flex items-center justify-center size-10 rounded-full bg-[#065fd4] text-white text-sm font-bold shrink-0">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[#0f0f0f] dark:text-[#f1f1f1] truncate">{user.displayName}</p>
              <p className="text-xs text-[#606060] dark:text-[#909090] truncate">{user.email}</p>
            </div>
          </div>
          <Link
            href="/history"
            className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#0f0f0f] dark:text-[#f1f1f1] hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
            onClick={() => setOpen(false)}
          >
            <History className="size-4 text-[#606060] dark:text-[#909090]" />
            {t.userMenu.watchHistory}
          </Link>
          <Link
            href="/admin"
            className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#0f0f0f] dark:text-[#f1f1f1] hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
            onClick={() => setOpen(false)}
          >
            <Settings className="size-4 text-[#606060] dark:text-[#909090]" />
            {t.userMenu.admin}
          </Link>
          <div className="border-t border-[#e5e5e5] dark:border-[#3f3f3f] mt-1 pt-1">
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#0f0f0f] dark:text-[#f1f1f1] hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
            >
              <LogOut className="size-4 text-[#606060] dark:text-[#909090]" />
              {t.common.logout}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function SearchBar() {
  const { t } = useLocale();
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    setQuery(searchParams.get("search") ?? "");
  }, [searchParams]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/?search=${encodeURIComponent(query.trim())}`);
    } else {
      router.push("/");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center flex-1 max-w-[640px]">
      <div className={cn(
        "flex items-center flex-1 h-10 px-4 rounded-l-full border transition-all",
        focused
          ? "border-[#1a73e8] ring-1 ring-[#1a73e8] bg-white dark:bg-[#212121]"
          : "border-[#ccc] dark:border-[#3f3f3f] bg-[#f8f8f8] dark:bg-[#272727]"
      )}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={t.common.search}
          className="flex-1 bg-transparent text-sm text-[#0f0f0f] dark:text-[#f1f1f1] outline-none placeholder:text-[#717171] dark:placeholder:text-[#909090]"
        />
        {query && (
          <button
            type="button"
            onClick={() => { setQuery(""); router.push("/"); }}
            className="text-[#606060] dark:text-[#909090] hover:text-[#0f0f0f] dark:hover:text-[#f1f1f1] transition-colors ml-2"
          >
            <X className="size-4" />
          </button>
        )}
      </div>
      <button
        type="submit"
        className="flex items-center justify-center h-10 w-16 bg-[#f8f8f8] dark:bg-[#272727] border border-l-0 border-[#ccc] dark:border-[#3f3f3f] rounded-r-full hover:bg-[#f0f0f0] dark:hover:bg-[#3f3f3f] transition-colors"
        aria-label={t.header.search}
      >
        <Search className="size-5 text-[#0f0f0f] dark:text-[#f1f1f1]" />
      </button>
    </form>
  );
}

export function Header() {
  const { toggle } = useSidebar();
  const { t } = useLocale();

  return (
    <header className="flex items-center gap-2 h-14 px-4 bg-white dark:bg-[#0f0f0f] sticky top-0 z-50 shrink-0">
      {/* Left: hamburger + logo */}
      <div className="flex items-center gap-1 shrink-0">
        <button
          onClick={toggle}
          className="flex items-center justify-center size-10 rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
          aria-label={t.header.menu}
        >
          <Menu className="size-5 text-[#0f0f0f] dark:text-[#f1f1f1]" />
        </button>
        <Link href="/" className="flex items-center gap-1 px-2">
          <div className="flex items-center justify-center size-7 bg-[#ff0000] rounded">
            <PlaySquare className="size-4 text-white" />
          </div>
          <span className="text-lg font-bold text-[#0f0f0f] dark:text-[#f1f1f1] leading-none hidden sm:block">
            MITENE
          </span>
        </Link>
      </div>

      {/* Center: search */}
      <div className="flex items-center gap-2 flex-1 justify-center px-2">
        <Suspense fallback={
          <div className="flex-1 max-w-[640px] h-10 bg-[#f2f2f2] dark:bg-[#272727] rounded-full animate-pulse" />
        }>
          <SearchBar />
        </Suspense>
        <button
          className="flex items-center justify-center size-10 rounded-full bg-[#f2f2f2] dark:bg-[#272727] hover:bg-[#e5e5e5] dark:hover:bg-[#3f3f3f] transition-colors shrink-0"
          aria-label={t.header.voiceSearch}
        >
          <Mic className="size-5 text-[#0f0f0f] dark:text-[#f1f1f1]" />
        </button>
      </div>

      {/* Right: actions + user */}
      <div className="flex items-center gap-1 shrink-0">
        <Link
          href="/admin"
          className="hidden sm:flex items-center gap-1.5 h-9 px-3 rounded-full border border-[#ccc] dark:border-[#3f3f3f] text-sm font-medium text-[#0f0f0f] dark:text-[#f1f1f1] hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
        >
          <RefreshCw className="size-4" />
          <span>{t.common.sync}</span>
        </Link>
        <button
          className="flex items-center justify-center size-10 rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
          aria-label={t.header.notifications}
        >
          <Bell className="size-5 text-[#0f0f0f] dark:text-[#f1f1f1]" />
        </button>
        <LanguageToggle />
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
