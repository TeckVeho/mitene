"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useLocale } from "@/lib/locale-context";
import { Loader2, ThumbsUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { VideoCard } from "@/components/videos/video-card";

export default function LikedPage() {
  const { t } = useLocale();
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    api.getCurrentUser().then((u) => setIsLoggedIn(!!u));
  }, []);

  const { data: videos = [], isLoading } = useQuery({
    queryKey: ["liked-videos"],
    queryFn: () => api.getLikedVideos(),
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
          <ThumbsUp className="size-8 text-muted-foreground/50" />
        </div>
        <h2 className="text-base font-semibold text-foreground mb-2">{t.liked.loginRequired}</h2>
        <p className="text-sm text-muted-foreground mb-5 max-w-sm">{t.liked.loginRequiredDesc}</p>
        <Button asChild>
          <Link href="/login">{t.common.login}</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-foreground">{t.liked.title}</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {videos.length > 0 ? `${videos.length}件` : t.liked.noVideosDesc}
        </p>
      </div>

      {videos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="size-14 rounded-full bg-muted flex items-center justify-center mb-4">
            <ThumbsUp className="size-7 text-muted-foreground/50" />
          </div>
          <h3 className="text-sm font-semibold text-foreground mb-2">{t.liked.noVideos}</h3>
          <p className="text-sm text-muted-foreground mb-4">{t.liked.noVideosDesc}</p>
          <Button asChild variant="outline" size="sm">
            <Link href="/">{t.liked.findVideos}</Link>
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-10">
          {videos.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      )}
    </div>
  );
}
