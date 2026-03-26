"use client";

import { use, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Download, RefreshCw, ArrowLeft, FileSpreadsheet, Loader2, Video } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { JobStatusBadge } from "@/components/jobs/job-status-badge";
import { JobProgress } from "@/components/jobs/job-progress";
import { useJob } from "@/hooks/use-jobs";
import { VIDEO_STYLE_LABELS } from "@/lib/types";
import { formatDateTime } from "@/lib/date-utils";
import { api } from "@/lib/api";

interface JobDetailPageProps {
  params: Promise<{ id: string }>;
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-start gap-4 py-2.5">
      <span className="text-xs text-muted-foreground font-medium w-32 shrink-0">{label}</span>
      <span className="text-sm text-foreground text-right">{value}</span>
    </div>
  );
}

export default function JobDetailPage({ params }: JobDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();

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
  const { data: job, isLoading, error } = useJob(id, canFetch);

  if (gateLoading || !gateUser || !gateUser.isAdmin) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          読み込み中...
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-sm font-medium text-foreground mb-2">ジョブが見つかりません</p>
        <p className="text-xs text-muted-foreground mb-5">
          指定されたジョブID: {id}
        </p>
        <Button asChild variant="outline" size="sm">
          <Link href="/jobs">
            <ArrowLeft className="size-3.5 mr-1.5" />
            一覧に戻る
          </Link>
        </Button>
      </div>
    );
  }

  const retryHref = "/admin";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center justify-center size-9 rounded-lg bg-muted shrink-0">
            <FileSpreadsheet className="size-4 text-muted-foreground" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-lg font-semibold text-foreground truncate">{job.csvFileNames}</h1>
              <JobStatusBadge status={job.status} />
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{job.notebookTitle}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {job.status === "completed" && (
            <Button asChild size="sm" className="gap-1.5">
              <a href={api.getDownloadUrl(job.id)} download>
                <Download className="size-3.5" />
                動画をダウンロード
              </a>
            </Button>
          )}
          {job.status === "error" && (
            <Button asChild variant="outline" size="sm" className="gap-1.5">
              <Link href={retryHref}>
                <RefreshCw className="size-3.5" />
                再試行
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* Error message */}
      {job.status === "error" && job.errorMessage && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
          <p className="text-sm font-medium text-destructive mb-1">エラーが発生しました</p>
          <p className="text-xs text-destructive/80">{job.errorMessage}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-5 gap-5">
        {/* Progress stepper */}
        <Card className="border-border md:col-span-3">
          <CardHeader className="pb-4">
            <CardTitle className="text-sm font-semibold">処理の進捗</CardTitle>
          </CardHeader>
          <CardContent>
            <JobProgress steps={job.steps} />
          </CardContent>
        </Card>

        {/* Job settings */}
        <Card className="border-border md:col-span-2">
          <CardHeader className="pb-4">
            <CardTitle className="text-sm font-semibold">ジョブ設定</CardTitle>
          </CardHeader>
          <CardContent className="space-y-0 divide-y divide-border">
            <>
              <DetailRow label="スタイル" value={job.style ? VIDEO_STYLE_LABELS[job.style as keyof typeof VIDEO_STYLE_LABELS]?.label ?? "—" : "—"} />
              <DetailRow label="フォーマット" value={job.format === "explainer" ? "解説型" : job.format === "brief" ? "短縮版" : "—"} />
            </>
            <DetailRow label="言語" value={job.language === "ja" ? "日本語" : job.language} />
            <DetailRow
              label="タイムアウト"
              value={`${Math.floor(job.timeout / 60)}分`}
            />
            <Separator className="my-0" />
            <DetailRow label="作成日時" value={formatDateTime(job.createdAt)} />
            {job.completedAt && (
              <DetailRow label="完了日時" value={formatDateTime(job.completedAt)} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Instructions */}
      <Card className="border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold">動画への指示文</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground leading-relaxed">{job.instructions}</p>
        </CardContent>
      </Card>
    </div>
  );
}
