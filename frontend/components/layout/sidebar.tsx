"use client";

import { useState } from "react";
import Link from "next/link";
import { LayoutDashboard, Video, History, ChevronLeft, ChevronRight, FileVideo, Mic, Settings } from "lucide-react";
import { SidebarItem } from "./sidebar-item";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const NAV_ITEMS = [
  { href: "/", icon: LayoutDashboard, label: "ダッシュボード", exact: true },
  { href: "/generate", icon: Video, label: "新規動画生成" },
  { href: "/generate-audio", icon: Mic, label: "新規音声生成" },
  { href: "/jobs", icon: History, label: "生成履歴" },
];

const BOTTOM_NAV_ITEMS = [
  { href: "/settings", icon: Settings, label: "設定" },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "relative flex flex-col h-screen bg-sidebar border-r border-sidebar-border transition-all duration-200 shrink-0",
        collapsed ? "w-14" : "w-60"
      )}
    >
      {/* Logo / App name */}
      <div className="flex items-center gap-2.5 px-3 py-4 border-b border-sidebar-border">
        <div className="flex items-center justify-center size-7 rounded-md bg-primary/10 text-primary shrink-0">
          <FileVideo className="size-4" />
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold truncate text-sidebar-foreground">
            NoteVideo
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {collapsed
          ? NAV_ITEMS.map((item) => (
              <Tooltip key={item.href} delayDuration={100}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    className="flex items-center justify-center size-9 rounded-md text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors mx-auto"
                  >
                    <item.icon className="size-4" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            ))
          : NAV_ITEMS.map((item) => (
              <SidebarItem key={item.href} {...item} />
            ))}
      </nav>

      {/* Bottom navigation (Settings etc.) */}
      <div className="px-2 py-2 border-t border-sidebar-border space-y-0.5">
        {collapsed
          ? BOTTOM_NAV_ITEMS.map((item) => (
              <Tooltip key={item.href} delayDuration={100}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    className="flex items-center justify-center size-9 rounded-md text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors mx-auto"
                  >
                    <item.icon className="size-4" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            ))
          : BOTTOM_NAV_ITEMS.map((item) => (
              <SidebarItem key={item.href} {...item} />
            ))}
        {!collapsed && (
          <p className="text-[11px] text-muted-foreground px-1 pt-1">NoteVideo v0.1.0</p>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-5 flex items-center justify-center size-6 rounded-full bg-sidebar border border-sidebar-border text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors shadow-sm z-10"
        aria-label={collapsed ? "サイドバーを展開" : "サイドバーを折りたたむ"}
      >
        {collapsed ? <ChevronRight className="size-3" /> : <ChevronLeft className="size-3" />}
      </button>
    </aside>
  );
}
