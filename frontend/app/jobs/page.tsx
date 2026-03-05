"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { JobTable } from "@/components/jobs/job-table";
import { useJobs } from "@/hooks/use-jobs";
import { Video } from "lucide-react";
import { cn } from "@/lib/utils";
import type { JobStatus } from "@/lib/types";

type FilterValue = "all" | JobStatus;

const FILTERS: { value: FilterValue; label: string }[] = [
  { value: "all", label: "すべて" },
  { value: "processing", label: "処理中" },
  { value: "completed", label: "完了" },
  { value: "error", label: "エラー" },
];

export default function JobsPage() {
  const [filter, setFilter] = useState<FilterValue>("all");
  const { data: jobs, isLoading } = useJobs(filter === "all" ? undefined : filter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">生成履歴</h1>
          <p className="text-sm text-muted-foreground mt-1">
            これまでに生成したすべての動画ジョブ
          </p>
        </div>
        <Button asChild size="sm" className="gap-1.5">
          <Link href="/generate">
            <Video className="size-3.5" />
            新規生成
          </Link>
        </Button>
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-lg w-fit">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-150",
              filter === f.value
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="rounded-lg border border-border">
          <div className="h-48 flex items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="size-4 border-2 border-muted-foreground/30 border-t-primary rounded-full animate-spin" />
              読み込み中...
            </div>
          </div>
        </div>
      ) : (
        <JobTable jobs={jobs ?? []} />
      )}
    </div>
  );
}
