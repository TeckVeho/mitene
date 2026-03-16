"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { VideoCard } from "@/components/videos/video-card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/locale-context";
import type { Category } from "@/lib/types";

function getChipLabels(t: ReturnType<typeof useLocale>["t"]) {
  return [
    { key: undefined as string | undefined, label: t.home.all },
    { key: "security", label: t.home.categorySecurity },
    { key: "development", label: t.home.categoryDevelopment },
    { key: "infrastructure", label: t.home.categoryInfrastructure },
    { key: "communication", label: t.home.categoryCommunication },
    { key: "misc", label: t.home.categoryMisc },
  ];
}

function FilterChips({
  categories,
  selected,
  onSelect,
  chipLabels,
}: {
  categories: Category[];
  selected?: string;
  onSelect: (slug?: string) => void;
  chipLabels: { key: string | undefined; label: string }[];
}) {
  return (
    <div className="flex items-center gap-3 overflow-x-auto scrollbar-hide py-3 px-4">
      <button
        onClick={() => onSelect(undefined)}
        className={cn(
          "shrink-0 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
          !selected
            ? "bg-[#0f0f0f] dark:bg-[#f1f1f1] text-white dark:text-[#0f0f0f]"
            : "bg-[#f2f2f2] dark:bg-[#272727] text-[#0f0f0f] dark:text-[#f1f1f1] hover:bg-[#e5e5e5] dark:hover:bg-[#3f3f3f]"
        )}
      >
        {chipLabels[0]!.label}
      </button>
      {categories.map((cat) => {
        const label = chipLabels.find((c) => c.key === cat.slug)?.label ?? cat.name;
        return (
          <button
            key={cat.id}
            onClick={() => onSelect(cat.slug)}
            className={cn(
              "shrink-0 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
              selected === cat.slug
                ? "bg-[#0f0f0f] dark:bg-[#f1f1f1] text-white dark:text-[#0f0f0f]"
                : "bg-[#f2f2f2] dark:bg-[#272727] text-[#0f0f0f] dark:text-[#f1f1f1] hover:bg-[#e5e5e5] dark:hover:bg-[#3f3f3f]"
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

function HomeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { t, locale } = useLocale();
  const chipLabels = getChipLabels(t);
  const selectedCategory = searchParams.get("category") ?? undefined;
  const searchQuery = searchParams.get("search") ?? undefined;

  const { data: categories = [] } = useQuery({
    queryKey: ["categories", locale],
    queryFn: () => api.getCategories({ locale }),
    staleTime: 60000,
  });

  const { data: videos = [], isLoading } = useQuery({
    queryKey: ["videos", selectedCategory, searchQuery, locale],
    queryFn: () =>
      api.getVideos({
        category: selectedCategory,
        search: searchQuery,
        limit: 48,
        locale,
      }),
    staleTime: 30000,
  });

  function setParam(key: string, value: string | undefined) {
    const p = new URLSearchParams(searchParams.toString());
    if (value) p.set(key, value);
    else p.delete(key);
    router.push(`/?${p.toString()}`);
  }

  const isSearchMode = !!searchQuery;
  const allCategories = categories.filter((c) => c.videoCount > 0);

  return (
    <div className="min-h-screen bg-white dark:bg-[#0f0f0f]">
      {/* Filter chips */}
      {!isSearchMode && (
        <div className="sticky top-0 z-10 bg-white dark:bg-[#0f0f0f] border-b border-[#e5e5e5] dark:border-[#3f3f3f]">
          <FilterChips
            categories={allCategories}
            selected={selectedCategory}
            onSelect={(slug) => setParam("category", slug)}
            chipLabels={chipLabels}
          />
        </div>
      )}

      {/* Search result header */}
      {isSearchMode && (
        <div className="px-4 pt-5 pb-2">
          <h2 className="text-lg font-medium text-[#0f0f0f] dark:text-[#f1f1f1]">
            「{searchQuery}」{t.home.searchResults}
          </h2>
          <p className="text-sm text-[#606060] dark:text-[#909090] mt-0.5">{videos.length}{t.home.videosCount}</p>
        </div>
      )}

      {/* Video grid */}
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
              {isSearchMode
                ? `「${searchQuery}」${t.home.noVideosSearch}`
                : selectedCategory
                ? t.home.noVideosCategory
                : t.home.noVideosSync}
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

export default function HomePage() {
  return (
    <Suspense fallback={
        <div className="flex items-center justify-center py-32">
        <Loader2 className="size-8 animate-spin text-[#606060] dark:text-[#909090]" />
      </div>
    }>
      <HomeContent />
    </Suspense>
  );
}
