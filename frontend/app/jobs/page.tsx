"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { JobTable } from "@/components/jobs/job-table";
import { useJobs } from "@/hooks/use-jobs";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { JobStatus } from "@/lib/types";

type StatusFilter = "all" | JobStatus;

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "すべて" },
  { value: "processing", label: "処理中" },
  { value: "completed", label: "完了" },
  { value: "error", label: "エラー" },
];

export default function JobsPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const { data: gateUser, isLoading: gateLoading } = useQuery({
    queryKey: ["current-user"],
    queryFn: () => api.getCurrentUser(),
  });

  useEffect(() => {
    if (gateLoading) return;
    if (!gateUser) {
      router.replace("/login");
      return;
    }
    if (!gateUser.isAdmin) {
      router.replace("/");
    }
  }, [gateLoading, gateUser, router]);

  const canFetch = gateUser?.isAdmin === true;
  const { data: jobs, isLoading } = useJobs(
    statusFilter === "all" ? undefined : statusFilter,
    canFetch,
  );

  if (gateLoading || !gateUser || !gateUser.isAdmin) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">動画生成ジョブ</h1>
          <p className="text-sm text-muted-foreground mt-1">
            NotebookLM動画生成ジョブの一覧
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
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
