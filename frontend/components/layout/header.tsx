"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronRight, Video, CheckCircle2, AlertCircle, LogIn, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStatus, useTriggerLogin } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import type { AuthStatusValue } from "@/lib/types";

const BREADCRUMB_MAP: Record<string, string> = {
  "": "ダッシュボード",
  generate: "新規動画生成",
  jobs: "生成履歴",
};

function getBreadcrumbs(pathname: string) {
  const segments = pathname.split("/").filter(Boolean);
  const crumbs: { label: string; href: string }[] = [{ label: "ダッシュボード", href: "/" }];

  let path = "";
  for (const seg of segments) {
    path += `/${seg}`;
    const label = BREADCRUMB_MAP[seg] ?? `ジョブ詳細`;
    crumbs.push({ label, href: path });
  }
  return crumbs;
}

const AUTH_CONFIG: Record<
  AuthStatusValue,
  { label: string; icon: React.ElementType; className: string }
> = {
  authenticated: {
    label: "NotebookLM 認証済み",
    icon: CheckCircle2,
    className: "text-green-600 bg-green-50 border-green-200",
  },
  session_expired: {
    label: "セッション期限切れ",
    icon: AlertCircle,
    className: "text-yellow-600 bg-yellow-50 border-yellow-200",
  },
  not_logged_in: {
    label: "未ログイン",
    icon: AlertCircle,
    className: "text-red-600 bg-red-50 border-red-200",
  },
};

function AuthBadge() {
  const { data, isLoading } = useAuthStatus();
  const { mutate: triggerLogin, isPending: isLoggingIn } = useTriggerLogin();

  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs text-muted-foreground bg-muted/30 border-border">
        <Loader2 className="size-3 animate-spin" />
        <span>確認中...</span>
      </div>
    );
  }

  const status = data?.status ?? "not_logged_in";
  const config = AUTH_CONFIG[status];
  const Icon = config.icon;
  const needsLogin = status !== "authenticated";

  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium",
          config.className
        )}
      >
        <Icon className="size-3" />
        <span>{config.label}</span>
      </div>

      {needsLogin && (
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5 h-7 text-xs"
          onClick={() => triggerLogin()}
          disabled={isLoggingIn}
        >
          {isLoggingIn ? (
            <>
              <Loader2 className="size-3 animate-spin" />
              ログイン中...
            </>
          ) : (
            <>
              <LogIn className="size-3" />
              {status === "session_expired" ? "再ログイン" : "ログイン"}
            </>
          )}
        </Button>
      )}
    </div>
  );
}

export function Header() {
  const pathname = usePathname();
  const breadcrumbs = getBreadcrumbs(pathname);
  const isRoot = pathname === "/";

  return (
    <header className="flex items-center justify-between h-12 px-6 border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-10">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1 text-sm" aria-label="パンくずリスト">
        {breadcrumbs.map((crumb, i) => (
          <span key={crumb.href} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="size-3.5 text-muted-foreground" />}
            {i === breadcrumbs.length - 1 ? (
              <span className="text-foreground font-medium">{crumb.label}</span>
            ) : (
              <Link
                href={crumb.href}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {crumb.label}
              </Link>
            )}
          </span>
        ))}
      </nav>

      {/* Right side */}
      <div className="flex items-center gap-3">
        <AuthBadge />

        {isRoot && (
          <Button asChild size="sm" className="gap-1.5">
            <Link href="/generate">
              <Video className="size-3.5" />
              新規動画を生成
            </Link>
          </Button>
        )}
      </div>
    </header>
  );
}
