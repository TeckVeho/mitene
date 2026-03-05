"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { JobTable } from "@/components/jobs/job-table";
import { useJobs } from "@/hooks/use-jobs";
import { Video, Mic } from "lucide-react";
import { cn } from "@/lib/utils";
import type { JobStatus, JobType } from "@/lib/types";

type StatusFilter = "all" | JobStatus;
type TypeFilter = "all" | JobType;

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "すべて" },
  { value: "processing", label: "処理中" },
  { value: "completed", label: "完了" },
  { value: "error", label: "エラー" },
];

const TYPE_FILTERS: { value: TypeFilter; label: string; icon: React.ElementType }[] = [
  { value: "all", label: "全種別", icon: Video },
  { value: "video", label: "動画", icon: Video },
  { value: "audio", label: "音声", icon: Mic },
];

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const { data: jobs, isLoading } = useJobs(
    statusFilter === "all" ? undefined : statusFilter,
    typeFilter === "all" ? undefined : typeFilter,
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">生成履歴</h1>
          <p className="text-sm text-muted-foreground mt-1">
            これまでに生成したすべてのジョブ（動画・音声）
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild size="sm" variant="outline" className="gap-1.5">
            <Link href="/generate-audio">
              <Mic className="size-3.5" />
              新規音声
            </Link>
          </Button>
          <Button asChild size="sm" className="gap-1.5">
            <Link href="/generate">
              <Video className="size-3.5" />
              新規動画
            </Link>
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {/* Type filter */}
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-lg">
          {TYPE_FILTERS.map((f) => {
            const Icon = f.icon;
            return (
              <button
                key={f.value}
                onClick={() => setTypeFilter(f.value)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-150",
                  typeFilter === f.value
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Icon className="size-3" />
                {f.label}
              </button>
            );
          })}
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-lg">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-150",
                statusFilter === f.value
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
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
