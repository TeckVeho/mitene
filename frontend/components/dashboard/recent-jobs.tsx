"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useJobs } from "@/hooks/use-jobs";
import { JobStatusBadge } from "@/components/jobs/job-status-badge";
import { VIDEO_STYLE_LABELS } from "@/lib/types";
import { formatDistanceToNow } from "@/lib/date-utils";
import { ArrowRight, FileSpreadsheet, Video } from "lucide-react";

export function RecentJobs() {
  const { data: jobs, isLoading } = useJobs();
  const recentJobs = jobs?.slice(0, 5) ?? [];

  return (
    <Card className="border-border">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-sm font-semibold text-foreground">最近のジョブ</CardTitle>
        <Button asChild variant="ghost" size="sm" className="text-xs text-muted-foreground h-auto py-1">
          <Link href="/jobs">
            すべて表示
            <ArrowRight className="size-3 ml-1" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-px px-4 pb-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-14 animate-pulse bg-muted rounded-md" />
            ))}
          </div>
        ) : recentJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="flex items-center justify-center size-12 rounded-full bg-muted mb-3">
              <Video className="size-5 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">まだ動画が生成されていません</p>
            <Button asChild size="sm" className="mt-4">
              <Link href="/generate">最初の動画を生成する</Link>
            </Button>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {recentJobs.map((job) => (
              <li key={job.id}>
                <Link
                  href={`/jobs/${job.id}`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-muted/40 transition-colors"
                >
                  <div className="flex items-center justify-center size-8 rounded-md bg-muted shrink-0">
                    <FileSpreadsheet className="size-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <p className="text-sm font-medium truncate text-foreground">{job.csvFileNames}</p>
                      <JobStatusBadge status={job.status} />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {VIDEO_STYLE_LABELS[job.style].label}
                      </span>
                      <span className="text-muted-foreground text-xs">·</span>
                      <span className="text-xs text-muted-foreground">
                        {formatDistanceToNow(job.createdAt)}
                      </span>
                    </div>
                    {job.status === "processing" && (
                      <Progress className="h-1 mt-1.5" value={getProgress(job.currentStep)} />
                    )}
                  </div>
                  <ArrowRight className="size-3.5 text-muted-foreground shrink-0" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function getProgress(step?: string): number {
  const steps = ["create_notebook", "add_source", "generate_video", "wait_completion", "download_ready"];
  const idx = steps.indexOf(step ?? "");
  if (idx === -1) return 0;
  return ((idx + 1) / steps.length) * 100;
}
