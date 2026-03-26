"use client";

import { use, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocale } from "@/lib/locale-context";
import {
  ArrowLeft,
  CheckCircle2,
  Tag,
  Clock,
  PlayCircle,
  Loader2,
  FileText,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  ClockPlus,
  ThumbsUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { VideoCard } from "@/components/videos/video-card";
import { CommentSection } from "@/components/videos/comment-section";
import { LoginRequiredDialog } from "@/components/auth/login-required-dialog";
import { api } from "@/lib/api";
import { playRandomCelebration } from "@/lib/celebration-animations";
import { cn } from "@/lib/utils";

function formatDuration(sec?: number, t?: ReturnType<typeof useLocale>["t"]): string {
  if (!sec) return "—";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (!t) return `${m}分${s}秒`;
  // ja: "分", "秒" -> "5分30秒" | vi: " phút ", " giây" -> "5 phút 30 giây"
  return `${m}${t.videoDetail.min}${s}${t.videoDetail.sec}`;
}

function formatDate(dateStr?: string, locale?: string): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString(locale === "vi" ? "vi-VN" : "ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

interface Props {
  params: Promise<{ id: string }>;
}

export default function VideoPlayerPage({ params }: Props) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { t, locale } = useLocale();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [markAsWatchedDone, setMarkAsWatchedDone] = useState(false);
  const [showMarkdown, setShowMarkdown] = useState(false);
  const [loginPromptOpen, setLoginPromptOpen] = useState(false);

  const { data: video, isLoading, error } = useQuery({
    queryKey: ["videos", id],
    queryFn: () => api.getVideo(id),
    enabled: !!id,
  });

  const { data: currentUser } = useQuery({
    queryKey: ["current-user"],
    queryFn: () => api.getCurrentUser(),
  });
  const isLoggedIn = !!currentUser;

  const { data: relatedVideos = [] } = useQuery({
    queryKey: ["videos", "related", video?.categorySlug, locale],
    queryFn: () =>
      api.getVideos({
        category: video?.categorySlug,
        status: "ready",
        limit: 8,
        locale,
      }),
    enabled: !!video?.categorySlug,
  });

  const watchMutation = useMutation({
    mutationFn: () => api.recordWatch(id),
    onSuccess: () => {
      setMarkAsWatchedDone(true);
      queryClient.invalidateQueries({ queryKey: ["videos", id] });
      queryClient.invalidateQueries({ queryKey: ["watch-history"] });
      // ランダムで紙吹雪などのアニメーションを表示
      playRandomCelebration();
    },
  });

  const watchLaterMutation = useMutation({
    mutationFn: () => api.toggleWatchLater(id),
    onSuccess: (data) => {
      queryClient.setQueryData(["videos", id], (prev: typeof video) =>
        prev ? { ...prev, watchLater: data.added } : prev
      );
      queryClient.invalidateQueries({ queryKey: ["watch-later"] });
      queryClient.invalidateQueries({ queryKey: ["videos"] });
    },
  });

  const likedMutation = useMutation({
    mutationFn: () => api.toggleLiked(id),
    onSuccess: (data) => {
      queryClient.setQueryData(["videos", id], (prev: typeof video) =>
        prev ? { ...prev, liked: data.added } : prev
      );
      queryClient.invalidateQueries({ queryKey: ["liked-videos"] });
      queryClient.invalidateQueries({ queryKey: ["videos"] });
    },
  });

  const requestMarkWatched = useCallback(() => {
    if (!isLoggedIn) {
      setLoginPromptOpen(true);
      return;
    }
    watchMutation.mutate();
  }, [isLoggedIn, watchMutation]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          <span className="text-sm">{t.videoDetail.loading}</span>
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center">
        <p className="text-base font-semibold text-foreground mb-2">{t.videoDetail.notFound}</p>
        <p className="text-sm text-muted-foreground mb-5">ID: {id}</p>
        <Button asChild variant="outline" size="sm">
          <Link href="/">
            <ArrowLeft className="size-3.5 mr-1.5" />
            {t.videoDetail.backToHome}
          </Link>
        </Button>
      </div>
    );
  }

  const isAlreadyWatched = video.watched || markAsWatchedDone;
  const related = relatedVideos.filter((v) => v.id !== id).slice(0, 6);
  const streamUrl = video.jobId ? api.getVideoStreamUrl(id, video.jobId) : "";

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-6">
      <div className="flex flex-col xl:flex-row gap-6">
        {/* Main: Player + Info */}
        <div className="flex-1 min-w-0 space-y-5">
          {/* Back button */}
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="size-4" />
            {t.common.back}
          </button>

          {/* Video player */}
          <div className="relative bg-black rounded-2xl overflow-hidden shadow-xl aspect-video">
            {streamUrl ? (
              <video
                ref={videoRef}
                src={streamUrl}
                controls
                className="w-full h-full"
                onEnded={requestMarkWatched}
                poster={video.thumbnailUrl ?? undefined}
              />
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-gradient-to-br from-muted/80 to-muted/50">
                <PlayCircle className="size-16 text-muted-foreground/40" />
                <div className="text-center">
                  <p className="text-sm font-medium text-muted-foreground">{t.videoDetail.videoPreview}</p>
                  <p className="text-xs text-muted-foreground/70 mt-1">
                    {t.videoDetail.videoPreviewDesc}
                  </p>
                </div>
              </div>
            )}

            {/* Watched overlay hint */}
            {isAlreadyWatched && (
              <div className="absolute top-3 right-3 flex items-center gap-1.5 bg-black/70 text-white text-xs px-3 py-1.5 rounded-full backdrop-blur-sm">
                <CheckCircle2 className="size-3.5 text-green-400" />
                {t.videoDetail.watched}
              </div>
            )}
          </div>

          {/* Title & Meta */}
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-4">
              <h1 className="text-xl font-bold text-foreground leading-snug">{video.title}</h1>
              <div className="flex items-center gap-3 shrink-0">
                {!isAlreadyWatched && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5"
                    onClick={requestMarkWatched}
                    disabled={watchMutation.isPending}
                  >
                    {watchMutation.isPending ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="size-3.5" />
                    )}
                    {t.videoDetail.markWatched}
                  </Button>
                )}
                {isAlreadyWatched && (
                  <span className="flex items-center gap-1.5 text-sm text-green-600 font-medium">
                    <CheckCircle2 className="size-4" />
                    {t.videoDetail.watched}
                  </span>
                )}
              </div>
            </div>

            {/* Meta row */}
            {/* Action buttons: Watch later, Liked (logged in only) */}
            {isLoggedIn && (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                variant={video.watchLater ? "secondary" : "outline"}
                className="gap-1.5"
                onClick={() => watchLaterMutation.mutate()}
                disabled={watchLaterMutation.isPending}
                title={video.watchLater ? t.videoDetail.removeFromWatchLater : t.videoDetail.addToWatchLater}
              >
                {watchLaterMutation.isPending ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <ClockPlus className="size-3.5" />
                )}
                {video.watchLater ? t.videoDetail.removeFromWatchLater : t.videoDetail.addToWatchLater}
              </Button>
              <Button
                size="sm"
                variant={video.liked ? "secondary" : "outline"}
                className={cn("gap-1.5", video.liked && "text-red-600")}
                onClick={() => likedMutation.mutate()}
                disabled={likedMutation.isPending}
                title={video.liked ? t.videoDetail.removeFromLiked : t.videoDetail.addToLiked}
              >
                {likedMutation.isPending ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <ThumbsUp className="size-3.5" />
                )}
                {video.liked ? t.videoDetail.removeFromLiked : t.videoDetail.addToLiked}
              </Button>
            </div>
            )}

            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span>
                {t.videoDetail.viewers}: {(video.viewerCount ?? 0).toLocaleString()} · {t.videoDetail.views}: {(video.viewCount ?? 0).toLocaleString()}
              </span>
              {video.categoryName && (
                <Link
                  href={`/?category=${video.categorySlug}`}
                  className="flex items-center gap-1.5 hover:text-foreground transition-colors"
                >
                  <Tag className="size-3.5" />
                  {video.categoryName}
                </Link>
              )}
              {video.durationSec && (
                <span className="flex items-center gap-1.5">
                  <Clock className="size-3.5" />
                  {formatDuration(video.durationSec, t)}
                </span>
              )}
              {video.publishedAt && (
                <span className="text-muted-foreground/70">
                  {formatDate(video.publishedAt, locale)} {t.videoDetail.published}
                </span>
              )}
              {video.wikiUrl && (
                <a
                  href={video.wikiUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ExternalLink className="size-3.5" />
                  Wiki
                </a>
              )}
            </div>

            {/* Description */}
            {video.description && (
              <p className="text-sm text-muted-foreground leading-relaxed bg-muted/30 rounded-xl px-4 py-3">
                {video.description}
              </p>
            )}
          </div>

          {/* Markdown content accordion */}
          {video.articleId && (
            <div className="border border-border rounded-xl overflow-hidden">
              <button
                onClick={() => setShowMarkdown(!showMarkdown)}
                className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/40 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <FileText className="size-4 text-muted-foreground" />
                  {t.videoDetail.showMarkdown}
                </span>
                {showMarkdown ? (
                  <ChevronUp className="size-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="size-4 text-muted-foreground" />
                )}
              </button>
              {showMarkdown && (
                <div className="border-t border-border px-4 py-4 bg-muted/20">
                  <p className="text-xs text-muted-foreground italic">
                    {t.videoDetail.markdownNote}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Comments */}
          <div className="border-t border-[#e5e5e5] dark:border-[#3f3f3f] pt-6">
            <CommentSection
              videoId={id}
              isLoggedIn={isLoggedIn}
              onRequireLogin={() => setLoginPromptOpen(true)}
            />
          </div>
        </div>

        {/* Sidebar: Related videos */}
        {related.length > 0 && (
          <div className="xl:w-80 shrink-0 space-y-3">
            <h2 className="text-sm font-semibold text-foreground">
              {video.categoryName ? `${video.categoryName}${t.videoDetail.relatedVideos}` : t.videoDetail.relatedVideosFallback}
            </h2>
            <div className="space-y-3">
              {related.map((v) => (
                <VideoCard key={v.id} video={v} compact />
              ))}
            </div>
          </div>
        )}
      </div>

      <LoginRequiredDialog open={loginPromptOpen} onOpenChange={setLoginPromptOpen} />
    </div>
  );
}
