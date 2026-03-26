"use client";

import Link from "next/link";
import { PlayCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/locale-context";
import { VideoAdminMenu } from "@/components/videos/video-admin-menu";
import type { Video } from "@/lib/types";

const CATEGORY_COLORS: Record<string, string> = {
  security: "bg-red-600",
  development: "bg-blue-600",
  infrastructure: "bg-green-600",
  communication: "bg-yellow-500",
  misc: "bg-gray-600",
};

function formatDuration(sec?: number): string {
  if (!sec) return "";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatViewCount(count: number | undefined, viewsLabel: string): string {
  if (!count) return `0 ${viewsLabel}`;
  if (count >= 10000) return `${Math.floor(count / 1000)}K ${viewsLabel}`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K ${viewsLabel}`;
  return `${count} ${viewsLabel}`;
}

function timeAgo(dateStr: string | undefined, t: ReturnType<typeof useLocale>["t"]): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return t.videoCard.today;
  if (days === 1) return `1${t.videoCard.daysAgo}`;
  if (days < 7) return `${days}${t.videoCard.daysAgo}`;
  if (days < 30) return `${Math.floor(days / 7)}${t.videoCard.weeksAgo}`;
  if (days < 365) return `${Math.floor(days / 30)}${t.videoCard.monthsAgo}`;
  return `${Math.floor(days / 365)}${t.videoCard.yearsAgo}`;
}

function CategoryAvatar({ slug, name }: { slug?: string; name?: string }) {
  const colorClass = (slug && CATEGORY_COLORS[slug]) ?? "bg-gray-500";
  const initial = name ? name.slice(0, 1) : "?";
  return (
    <div className={cn(
      "size-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0",
      colorClass
    )}>
      {initial}
    </div>
  );
}

interface VideoCardProps {
  video: Video;
  compact?: boolean;
  /** Admin の編集・削除メニュー（ホームのグリッドなど） */
  showAdminMenu?: boolean;
}

export function VideoCard({ video, compact = false, showAdminMenu = false }: VideoCardProps) {
  const { t } = useLocale();
  const isReady = video.status === "ready";
  const href = isReady ? `/videos/${video.id}` : "#";

  if (compact) {
    return (
      <Link href={href} className="flex gap-2 group">
        {/* Compact thumbnail */}
        <div className="relative w-40 aspect-video rounded-xl overflow-hidden shrink-0 bg-[#f2f2f2] dark:bg-[#272727]">
          {video.thumbnailUrl ? (
            <img
              src={video.thumbnailUrl}
              alt={video.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <PlayCircle className="size-8 text-[#aaa] dark:text-[#606060]" />
            </div>
          )}
          {video.durationSec && (
            <span className="absolute bottom-1 right-1 bg-black/80 text-white text-[11px] px-1.5 py-0.5 rounded font-medium">
              {formatDuration(video.durationSec)}
            </span>
          )}
          {video.status === "generating" && (
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
              <Loader2 className="size-6 text-white animate-spin" />
            </div>
          )}
        </div>
        {/* Compact info */}
        <div className="flex-1 min-w-0 py-0.5">
          <h3 className="text-sm font-medium text-[#0f0f0f] dark:text-[#f1f1f1] line-clamp-2 leading-snug group-hover:text-[#000] dark:group-hover:text-white">
            {video.title}
          </h3>
          <p className="text-xs text-[#606060] dark:text-[#909090] mt-1">{video.categoryName}</p>
          <p className="text-xs text-[#606060] dark:text-[#909090]">
            {formatViewCount(video.viewCount, t.videoCard.views)} • {timeAgo(video.publishedAt, t)}
          </p>
        </div>
      </Link>
    );
  }

  return (
    <div className="group flex flex-col cursor-pointer">
      {/* Thumbnail */}
      <Link href={href} className="block">
        <div className="relative aspect-video rounded-xl overflow-hidden bg-[#f2f2f2] dark:bg-[#272727]">
          {video.thumbnailUrl ? (
            <img
              src={video.thumbnailUrl}
              alt={video.title}
              className="w-full h-full object-cover group-hover:rounded-none transition-all duration-200"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <PlayCircle className="size-16 text-[#aaa] dark:text-[#606060]" />
            </div>
          )}

          {/* Duration badge */}
          {video.durationSec && isReady && (
            <span className="absolute bottom-1.5 right-1.5 bg-black/80 text-white text-[12px] px-1.5 py-0.5 rounded font-medium">
              {formatDuration(video.durationSec)}
            </span>
          )}

          {/* Generating overlay */}
          {video.status === "generating" && (
            <div className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center gap-2">
              <Loader2 className="size-8 text-white animate-spin" />
              <span className="text-white text-xs font-medium">{t.common.generating}...</span>
            </div>
          )}

          {/* Watched progress bar */}
          {video.watched && isReady && (
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/20">
              <div className="h-full bg-[#ff0000] w-full" />
            </div>
          )}
        </div>
      </Link>

      {/* Info row */}
      <div className="flex gap-3 mt-3 items-start">
        {/* Channel avatar */}
        <Link href={`/?category=${video.categorySlug ?? ""}`} className="shrink-0 mt-0.5">
          <CategoryAvatar slug={video.categorySlug} name={video.categoryName} />
        </Link>

        {/* Video details + optional admin menu */}
        <div className="flex-1 min-w-0 flex gap-1 justify-between items-start">
          <div className="min-w-0 flex-1">
            <Link href={href}>
              <h3 className="text-sm font-semibold text-[#0f0f0f] dark:text-[#f1f1f1] line-clamp-2 leading-snug hover:text-black dark:hover:text-white">
                {video.title}
              </h3>
            </Link>
            <Link href={`/?category=${video.categorySlug ?? ""}`}>
              <p className="text-xs text-[#606060] dark:text-[#909090] mt-1 hover:text-[#0f0f0f] dark:hover:text-[#f1f1f1] transition-colors">
                {video.categoryName}
              </p>
            </Link>
            <p className="text-xs text-[#606060] dark:text-[#909090]">
              {formatViewCount(video.viewCount, t.videoCard.views)}
              {video.publishedAt && ` • ${timeAgo(video.publishedAt, t)}`}
            </p>
          </div>
          {showAdminMenu ? (
            <div className="shrink-0 -mr-1 -mt-0.5" onClick={(e) => e.stopPropagation()}>
              <VideoAdminMenu video={video} />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
