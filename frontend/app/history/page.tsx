"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useLocale } from "@/lib/locale-context";
import { Loader2, History, CheckCircle2, Tag, Clock, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { WatchRecord } from "@/lib/types";

function formatRelativeTime(dateStr: string, t: ReturnType<typeof useLocale>["t"]): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return t.history.justNow;
  if (mins < 60) return `${mins}${t.history.minsAgo}`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}${t.history.hoursAgo}`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}${t.history.daysAgo}`;
  return new Date(dateStr).toLocaleDateString("ja-JP", { month: "short", day: "numeric" });
}

function WatchHistoryItem({ record, t }: { record: WatchRecord; t: ReturnType<typeof useLocale>["t"] }) {
  return (
    <Link
      href={`/videos/${record.videoId}`}
      className="flex items-start gap-4 p-4 rounded-xl hover:bg-muted/40 transition-colors group"
    >
      {/* Thumbnail placeholder */}
      <div className="size-16 rounded-lg bg-muted flex items-center justify-center shrink-0 group-hover:bg-muted/60 transition-colors">
        <PlayCircle className="size-7 text-muted-foreground/50 group-hover:text-primary/60 transition-colors" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-foreground line-clamp-2 group-hover:text-primary transition-colors">
          {record.videoTitle ?? t.history.unknownTitle}
        </h3>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          {record.categoryName && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Tag className="size-3" />
              {record.categoryName}
            </span>
          )}
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="size-3" />
            {formatRelativeTime(record.watchedAt, t)}
          </span>
          {record.completed && (
            <span className="flex items-center gap-1 text-xs text-green-600">
              <CheckCircle2 className="size-3" />
              {t.history.watched}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}

export default function HistoryPage() {
  const { t } = useLocale();
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    api.getCurrentUser().then((u) => setIsLoggedIn(!!u));
  }, []);

  const { data: history = [], isLoading } = useQuery({
    queryKey: ["watch-history"],
    queryFn: () => api.getWatchHistory(),
    enabled: isLoggedIn === true,
  });

  if (isLoggedIn === null || isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!isLoggedIn) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center px-4">
        <div className="size-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <History className="size-8 text-muted-foreground/50" />
        </div>
        <h2 className="text-base font-semibold text-foreground mb-2">{t.history.loginRequired}</h2>
        <p className="text-sm text-muted-foreground mb-5 max-w-sm">
          {t.history.loginRequiredDesc}
        </p>
        <Button asChild>
          <Link href="/login">{t.common.login}</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-foreground">{t.history.title}</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {history.length > 0 ? `${history.length}${t.history.recordsCount}` : t.history.emptySubtitle}
        </p>
      </div>

      {history.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="size-14 rounded-full bg-muted flex items-center justify-center mb-4">
            <History className="size-7 text-muted-foreground/50" />
          </div>
          <h3 className="text-sm font-semibold text-foreground mb-2">{t.history.noHistory}</h3>
          <p className="text-sm text-muted-foreground mb-4">{t.history.noHistoryDesc}</p>
          <Button asChild variant="outline" size="sm">
            <Link href="/">{t.history.findVideos}</Link>
          </Button>
        </div>
      ) : (
        <div className="bg-card rounded-2xl border border-border overflow-hidden divide-y divide-border">
          {history.map((record) => (
            <WatchHistoryItem key={record.id} record={record} t={t} />
          ))}
        </div>
      )}
    </div>
  );
}
