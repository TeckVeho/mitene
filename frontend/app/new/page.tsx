"use client";

import { Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { VideoCard } from "@/components/videos/video-card";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/locale-context";

function NewContent() {
  const { t, locale } = useLocale();
  const [publishedAfter] = useState(
    () => new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
  );

  const { data: videos = [], isLoading } = useQuery({
    queryKey: ["videos", "new", publishedAfter, locale],
    queryFn: () =>
      api.getVideos({
        publishedAfter,
        limit: 48,
        locale,
      }),
    staleTime: 30000,
  });

  return (
    <div className="min-h-screen bg-white dark:bg-[#0f0f0f]">
      <div className="px-4 pt-5 pb-2">
        <h2 className="text-lg font-medium text-[#0f0f0f] dark:text-[#f1f1f1]">{t.sidebar.new}</h2>
        <p className="text-sm text-[#606060] dark:text-[#909090] mt-0.5">
          {t.new.subtitle}
        </p>
      </div>

      <div className="px-4 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-32">
            <Loader2 className="size-8 animate-spin text-[#606060] dark:text-[#909090]" />
          </div>
        ) : videos.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 text-center">
            <div className="size-20 rounded-full bg-[#f2f2f2] dark:bg-[#272727] flex items-center justify-center mb-4">
              <Loader2 className="size-10 text-[#aaa] dark:text-[#606060]" />
            </div>
            <h3 className="text-base font-medium text-[#0f0f0f] dark:text-[#f1f1f1] mb-2">{t.home.noVideos}</h3>
            <p className="text-sm text-[#606060] dark:text-[#909090] max-w-sm">
              {t.new.noVideos}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-10">
            {videos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function NewPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-32">
          <Loader2 className="size-8 animate-spin text-[#606060] dark:text-[#909090]" />
        </div>
      }
    >
      <NewContent />
    </Suspense>
  );
}
