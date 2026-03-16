"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale } from "@/lib/locale-context";
import {
  Home,
  History,
  Settings,
  GraduationCap,
  Shield,
  Code2,
  Server,
  MessageSquare,
  BookOpen,
  ChevronDown,
  ThumbsUp,
  Clock,
  Flame,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useSidebar } from "./layout-client";
import type { Category } from "@/lib/types";

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  security: Shield,
  development: Code2,
  infrastructure: Server,
  communication: MessageSquare,
  misc: BookOpen,
};

const CATEGORY_COLORS: Record<string, string> = {
  security: "text-red-600",
  development: "text-blue-600",
  infrastructure: "text-green-600",
  communication: "text-yellow-600",
  misc: "text-gray-600",
};

interface NavItemProps {
  href: string;
  icon: React.ElementType;
  label: string;
  exact?: boolean;
  mini: boolean;
  badge?: number;
}

function NavItem({ href, icon: Icon, label, exact, mini, badge }: NavItemProps) {
  const pathname = usePathname();
  const isActive = exact ? pathname === href : pathname.startsWith(href);

  const content = (
    <Link
      href={href}
      className={cn(
        "flex items-center rounded-xl transition-colors",
        mini
          ? "flex-col gap-1 px-1 py-3 w-full justify-center text-center"
          : "flex-row gap-3 px-3 py-2 w-full",
        isActive
          ? "bg-[#f2f2f2] dark:bg-[#272727] font-semibold"
          : "hover:bg-[#f2f2f2] dark:hover:bg-[#272727]"
      )}
    >
      <div className="relative shrink-0">
        <Icon className={cn("size-5", "text-[#0f0f0f] dark:text-[#f1f1f1]")} />
        {badge !== undefined && badge > 0 && (
          <span className="absolute -top-1 -right-1 bg-[#ff0000] text-white text-[9px] font-bold rounded-full size-4 flex items-center justify-center">
            {badge > 9 ? "9+" : badge}
          </span>
        )}
      </div>
      <span className={cn(
        "text-[#0f0f0f] dark:text-[#f1f1f1]",
        mini ? "text-[10px] leading-tight" : "text-sm truncate",
        isActive && "font-semibold"
      )}>
        {label}
      </span>
    </Link>
  );

  if (mini) {
    return (
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right" className="text-xs">{label}</TooltipContent>
      </Tooltip>
    );
  }
  return content;
}

function SectionDivider({ mini }: { mini: boolean }) {
  if (mini) return <div className="my-1 mx-3 border-t border-[#e5e5e5] dark:border-[#3f3f3f]" />;
  return <div className="my-2 border-t border-[#e5e5e5] dark:border-[#3f3f3f]" />;
}

function CategoryNavItem({ category, mini }: { category: Category; mini: boolean }) {
  const pathname = usePathname();
  const href = `/?category=${category.slug}`;
  const isActive =
    pathname === "/" &&
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("category") === category.slug;

  const Icon = CATEGORY_ICONS[category.slug] ?? BookOpen;
  const colorClass = CATEGORY_COLORS[category.slug] ?? "text-[#606060]";

  const content = (
    <Link
      href={href}
      className={cn(
        "flex items-center rounded-xl transition-colors",
        mini
          ? "flex-col gap-1 px-1 py-3 w-full justify-center text-center"
          : "flex-row gap-3 px-3 py-2 w-full",
        isActive ? "bg-[#f2f2f2] dark:bg-[#272727] font-semibold" : "hover:bg-[#f2f2f2] dark:hover:bg-[#272727]"
      )}
    >
      <Icon className={cn("size-5 shrink-0", colorClass)} />
      {!mini && (
        <>
          <span className="text-sm text-[#0f0f0f] dark:text-[#f1f1f1] truncate flex-1">{category.name}</span>
          <span className="text-xs text-[#606060] dark:text-[#909090] shrink-0">{category.videoCount}</span>
        </>
      )}
      {mini && (
        <span className="text-[10px] text-[#0f0f0f] dark:text-[#f1f1f1] leading-tight truncate w-full text-center px-0.5">
          {category.name.slice(0, 4)}
        </span>
      )}
    </Link>
  );

  if (mini) {
    return (
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right" className="text-xs">
          {category.name} ({category.videoCount})
        </TooltipContent>
      </Tooltip>
    );
  }
  return content;
}

export function Sidebar() {
  const { open: sidebarOpen } = useSidebar();
  const { t, locale } = useLocale();
  const mini = !sidebarOpen;

  const { data: categories = [] } = useQuery({
    queryKey: ["categories", locale],
    queryFn: () => api.getCategories({ locale }),
    staleTime: 60000,
  });

  const visibleCategories = categories.filter((c) => c.videoCount > 0);

  return (
    <aside
      className={cn(
        "flex flex-col h-full bg-white dark:bg-[#0f0f0f] overflow-y-auto overflow-x-hidden transition-all duration-200 shrink-0",
        mini ? "w-[72px]" : "w-60"
      )}
    >
      <div className={cn("px-2 py-2 space-y-0.5", mini && "px-1")}>
        <NavItem href="/" icon={Home} label={t.sidebar.home} exact mini={mini} />
        <NavItem href="/new" icon={Flame} label={t.sidebar.new} mini={mini} />
      </div>

      <SectionDivider mini={mini} />

      {/* My page section */}
      {!mini && (
        <div className="px-4 pt-2 pb-1">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-[#0f0f0f] dark:text-[#f1f1f1]">{t.sidebar.myPage}</span>
            <ChevronDown className="size-4 text-[#606060] dark:text-[#909090]" />
          </div>
        </div>
      )}
      <div className={cn("px-2 pb-2 space-y-0.5", mini && "px-1")}>
        <NavItem href="/history" icon={History} label={t.sidebar.history} mini={mini} />
        <NavItem href="/watch-later" icon={Clock} label={t.sidebar.watchLater} mini={mini} />
        <NavItem href="/liked" icon={ThumbsUp} label={t.sidebar.likedVideos} mini={mini} />
      </div>

      <SectionDivider mini={mini} />

      {/* Categories / Channels */}
      {!mini && (
        <div className="px-4 pt-2 pb-1">
          <span className="text-sm font-semibold text-[#0f0f0f] dark:text-[#f1f1f1]">{t.sidebar.categories}</span>
        </div>
      )}
      <div className={cn("px-2 pb-2 space-y-0.5", mini && "px-1")}>
        {visibleCategories.map((cat) => (
          <CategoryNavItem key={cat.id} category={cat} mini={mini} />
        ))}
      </div>

      <SectionDivider mini={mini} />

      {/* Bottom */}
      <div className={cn("px-2 py-2 space-y-0.5", mini && "px-1")}>
        <NavItem href="/admin" icon={Settings} label={t.sidebar.admin} mini={mini} />
        <NavItem href="/admin" icon={GraduationCap} label={t.sidebar.administrator} mini={mini} />
      </div>

      {!mini && (
        <div className="px-4 py-4 text-[11px] text-[#606060] dark:text-[#909090] leading-relaxed">
          <p>{t.sidebar.copyright}</p>
          <p className="mt-1">v1.0.0</p>
        </div>
      )}
    </aside>
  );
}
