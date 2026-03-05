"use client";

import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { JobStatusBadge } from "./job-status-badge";
import type { Job } from "@/lib/types";
import { VIDEO_STYLE_LABELS } from "@/lib/types";
import { formatDistanceToNow } from "@/lib/date-utils";
import { api } from "@/lib/api";
import { ArrowRight, Download, FileSpreadsheet, Video } from "lucide-react";

interface JobTableProps {
  jobs: Job[];
}

function getProgress(step?: string): number {
  const steps = ["create_notebook", "add_source", "generate_video", "wait_completion", "download_ready"];
  const idx = steps.indexOf(step ?? "");
  if (idx === -1) return 0;
  return ((idx + 1) / steps.length) * 100;
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex items-center justify-center size-14 rounded-full bg-muted mb-4">
        <Video className="size-6 text-muted-foreground" />
      </div>
      <p className="text-sm font-medium text-foreground mb-1">動画がありません</p>
      <p className="text-xs text-muted-foreground mb-5">
        まだ動画が生成されていません。CSVファイルをアップロードして始めましょう。
      </p>
      <Button asChild size="sm">
        <Link href="/generate">最初の動画を生成する</Link>
      </Button>
    </div>
  );
}

export function JobTable({ jobs }: JobTableProps) {
  if (jobs.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/30 hover:bg-muted/30">
            <TableHead className="text-xs font-semibold text-muted-foreground w-[280px]">
              ファイル名
            </TableHead>
            <TableHead className="text-xs font-semibold text-muted-foreground">スタイル</TableHead>
            <TableHead className="text-xs font-semibold text-muted-foreground">フォーマット</TableHead>
            <TableHead className="text-xs font-semibold text-muted-foreground">ステータス</TableHead>
            <TableHead className="text-xs font-semibold text-muted-foreground">作成日時</TableHead>
            <TableHead className="text-xs font-semibold text-muted-foreground text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => (
            <TableRow key={job.id} className="group hover:bg-muted/20">
              <TableCell>
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center justify-center size-7 rounded-md bg-muted shrink-0">
                    <FileSpreadsheet className="size-3.5 text-muted-foreground" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate text-foreground max-w-[220px]">
                      {job.csvFileNames}
                    </p>
                    {job.status === "processing" && (
                      <Progress
                        className="h-1 mt-1 w-[140px]"
                        value={getProgress(job.currentStep)}
                      />
                    )}
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <span className="text-sm text-muted-foreground">
                  {VIDEO_STYLE_LABELS[job.style].label}
                </span>
              </TableCell>
              <TableCell>
                <span className="text-sm text-muted-foreground">
                  {job.format === "explainer" ? "解説型" : "短縮版"}
                </span>
              </TableCell>
              <TableCell>
                <JobStatusBadge status={job.status} />
              </TableCell>
              <TableCell>
                <span className="text-sm text-muted-foreground">
                  {formatDistanceToNow(job.createdAt)}
                </span>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  {job.status === "completed" && (
                    <Button
                      asChild
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs gap-1"
                    >
                      <a href={api.getDownloadUrl(job.id)} download>
                        <Download className="size-3" />
                        DL
                      </a>
                    </Button>
                  )}
                  <Button asChild variant="ghost" size="sm" className="h-7 text-xs gap-1">
                    <Link href={`/jobs/${job.id}`}>
                      詳細
                      <ArrowRight className="size-3" />
                    </Link>
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
