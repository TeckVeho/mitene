"use client";

import { useState, useEffect, lazy, Suspense } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocale } from "@/lib/locale-context";
import {
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
  Video,
  Settings,
  BookOpen,
  FolderOpen,
  Play,
  Monitor,
  RefreshCw,
  UploadCloud,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const RemoteLoginModal = lazy(() => import("@/components/auth/RemoteLoginModal"));
const UploadSessionModal = lazy(() => import("@/components/auth/UploadSessionModal"));
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AuthStatusValue, WikiDirectory } from "@/lib/types";

function getAuthConfig(t: ReturnType<typeof useLocale>["t"]): Record<AuthStatusValue, { label: string; icon: React.ElementType; className: string }> {
  return {
    authenticated: {
      label: t.admin.authenticated,
      icon: CheckCircle2,
      className: "text-green-600 bg-green-50 border-green-200",
    },
    session_expired: {
      label: t.admin.sessionExpired,
      icon: AlertCircle,
      className: "text-amber-600 bg-amber-50 border-amber-200",
    },
    not_logged_in: {
      label: t.admin.notLoggedIn,
      icon: AlertCircle,
      className: "text-red-600 bg-red-50 border-red-200",
    },
  };
}

function VideoStatusBadge({ status, t }: { status?: string | null; t: ReturnType<typeof useLocale>["t"] }) {
  if (!status) return <span className="text-xs text-muted-foreground">{t.admin.notGenerated}</span>;
  const map: Record<string, { label: string; className: string }> = {
    ready: { label: t.admin.published, className: "text-green-700 bg-green-50" },
    generating: { label: t.admin.generatingStatus, className: "text-amber-700 bg-amber-50" },
    error: { label: t.admin.errorStatus, className: "text-red-700 bg-red-50" },
  };
  const cfg = map[status] ?? { label: status, className: "text-muted-foreground bg-muted" };
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", cfg.className)}>
      {cfg.label}
    </span>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { t, locale } = useLocale();
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [remoteLoginOpen, setRemoteLoginOpen] = useState(false);
  const [credentialModalOpen, setCredentialModalOpen] = useState(false);
  const AUTH_CONFIG = getAuthConfig(t);

  const { data: gateUser, isLoading: gateAuthLoading } = useQuery({
    queryKey: ["current-user"],
    queryFn: () => api.getCurrentUser(),
  });

  useEffect(() => {
    if (gateAuthLoading) return;
    if (!gateUser) {
      router.replace("/login");
      return;
    }
    if (!gateUser.isAdmin) {
      router.replace("/");
    }
  }, [gateAuthLoading, gateUser, router]);

  const { data: authStatus } = useQuery({
    queryKey: ["auth-status"],
    queryFn: () => api.getAuthStatus(),
    refetchInterval: 30000,
    enabled: gateUser?.isAdmin === true,
  });

  const { data: syncStatus, refetch: refetchSyncStatus } = useQuery({
    queryKey: ["wiki-sync-status"],
    queryFn: () => api.getWikiSyncStatus(),
    refetchInterval: 10000,
    enabled: gateUser?.isAdmin === true,
  });

  const { data: directories = [], isLoading: directoriesLoading } = useQuery({
    queryKey: ["wiki-directories"],
    queryFn: () => api.getWikiDirectories(),
    staleTime: 60000,
    enabled: gateUser?.isAdmin === true,
  });

  const [selectedDir, setSelectedDir] = useState<string>("__none__");
  const [selectedPartPaths, setSelectedPartPaths] = useState<string[]>([]);

  const selectedDirectory = directories.find((d) => d.path === selectedDir);
  const selectedDirectoryFiles = selectedDirectory?.files ?? [];
  const hasPartSelector = selectedDir !== "__none__" && (selectedDirectory?.count ?? 0) >= 2 && selectedDirectoryFiles.length > 0;
  const isAllPartsSelected = hasPartSelector && selectedPartPaths.length === selectedDirectoryFiles.length;

  const toggleAllParts = () => {
    if (!hasPartSelector) return;
    if (isAllPartsSelected) {
      setSelectedPartPaths([]);
      return;
    }
    setSelectedPartPaths(selectedDirectoryFiles.map((f) => f.path));
  };

  const togglePart = (path: string) => {
    setSelectedPartPaths((prev) => (
      prev.includes(path)
        ? prev.filter((p) => p !== path)
        : [...prev, path]
    ));
  };

  const { mutate: triggerSyncFromGit, isPending: isSyncingFromGit } = useMutation({
    mutationFn: () => api.triggerWikiSyncFromGit(),
    onSuccess: (data) => {
      setSyncMessage(data.message);
      setTimeout(() => {
        void queryClient.invalidateQueries({ queryKey: ["wiki-directories"] });
        void refetchSyncStatus();
      }, 2500);
    },
  });

  const { mutate: triggerSyncFromDir, isPending: isSyncingFromDir } = useMutation({
    mutationFn: (payload: { path?: string; paths?: string[] }) => api.triggerWikiSyncFromDirectory(payload),
    onSuccess: (data) => {
      const msg = data.status === "success"
        ? (locale === "vi"
          ? `Đã bắt đầu tạo ${data.jobs_created} video từ thư mục đã chọn`
          : `選択したディレクトリから${data.jobs_created}件の動画生成を開始しました`)
        : data.status === "no_files"
        ? data.message ?? t.admin.noDirectories
        : data.message ?? t.admin.syncStarted;
      setSyncMessage(msg);
      setTimeout(() => refetchSyncStatus(), 2000);
      queryClient.invalidateQueries({ queryKey: ["admin-articles"] });
    },
  });

  const { data: articles = [], isLoading: articlesLoading } = useQuery({
    queryKey: ["admin-articles"],
    queryFn: () => api.getAdminArticles(),
    staleTime: 30000,
    enabled: gateUser?.isAdmin === true,
  });

  const { data: jobStats } = useQuery({
    queryKey: ["jobs-stats"],
    queryFn: () => api.getStats(),
    refetchInterval: 15000,
    enabled: gateUser?.isAdmin === true,
  });

  if (gateAuthLoading || !gateUser || !gateUser.isAdmin) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const authState = authStatus?.status ?? "not_logged_in";
  const authCfg = AUTH_CONFIG[authState];
  const AuthIcon = authCfg.icon;

  const stats = [
    { label: t.admin.totalArticles, value: articles.length, icon: FileText, color: "text-blue-600" },
    { label: t.admin.publishedVideos, value: articles.filter(a => a.latestVideoStatus === "ready").length, icon: Video, color: "text-green-600" },
    { label: t.admin.generating, value: jobStats?.processing ?? 0, icon: Loader2, color: "text-amber-600" },
    { label: t.admin.errors, value: jobStats?.error ?? 0, icon: AlertCircle, color: "text-red-600" },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-foreground">{t.admin.title}</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {t.admin.subtitle}
        </p>
      </div>

      {syncMessage && (
        <div className="flex items-center gap-3 px-4 py-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700">
          <CheckCircle2 className="size-4 shrink-0" />
          {syncMessage}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="border-border">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center gap-3">
                <div className={cn("size-9 rounded-lg bg-muted flex items-center justify-center", stat.color)}>
                  <stat.icon className="size-5" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{stat.value}</p>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* ディレクトリから動画作成 */}
        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <FolderOpen className="size-4" />
              {t.admin.createFromDirectory}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => triggerSyncFromGit()}
                disabled={isSyncingFromGit || syncStatus?.is_syncing || isSyncingFromDir}
              >
                {isSyncingFromGit ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="size-3.5" />
                )}
                {t.admin.syncWikiFromGit}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              {t.admin.selectDirectory}
            </p>
            {directoriesLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                {t.common.loading}
              </div>
            ) : directories.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t.admin.noDirectories}</p>
            ) : (
              <div className="space-y-3">
                <select
                  value={selectedDir}
                  onChange={(e) => {
                    const nextDir = e.target.value;
                    setSelectedDir(nextDir);
                    if (nextDir === "__none__") {
                      setSelectedPartPaths([]);
                      return;
                    }
                    const nextDirectory = directories.find((d: WikiDirectory) => d.path === nextDir);
                    const nextFiles = nextDirectory?.files ?? [];
                    if ((nextDirectory?.count ?? 0) >= 2 && nextFiles.length > 0) {
                      setSelectedPartPaths(nextFiles.map((f) => f.path));
                    } else {
                      setSelectedPartPaths([]);
                    }
                  }}
                  className="flex h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="__none__">{t.admin.selectDirectory}</option>
                  {directories.map((d) => (
                    <option key={d.path} value={d.path}>
                      {d.label} ({d.count})
                    </option>
                  ))}
                </select>
                {hasPartSelector && (
                  <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-medium text-foreground">{t.admin.selectParts}</p>
                      <Button
                        type="button"
                        size="sm"
                        variant={isAllPartsSelected ? "secondary" : "outline"}
                        className="h-7 px-2 text-xs"
                        onClick={toggleAllParts}
                      >
                        {t.admin.allParts}
                      </Button>
                    </div>
                    <div className="max-h-40 overflow-auto rounded-md border bg-background px-2 py-1.5 space-y-1">
                      {selectedDirectoryFiles.map((f) => {
                        const checked = selectedPartPaths.includes(f.path);
                        return (
                          <label
                            key={f.path}
                            className={cn(
                              "flex items-center gap-2 rounded px-1.5 py-1 text-sm cursor-pointer hover:bg-muted/60",
                              checked && "bg-muted"
                            )}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => togglePart(f.path)}
                              className="size-4 accent-primary"
                            />
                            <span className="truncate">{f.fileName}</span>
                          </label>
                        );
                      })}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {locale === "vi"
                        ? `Đã chọn ${selectedPartPaths.length}/${selectedDirectoryFiles.length} file`
                        : `${selectedPartPaths.length}/${selectedDirectoryFiles.length} 件を選択中`}
                    </p>
                    <p className="text-xs text-muted-foreground">{t.admin.partHint}</p>
                  </div>
                )}
                <div className="flex justify-end">
                  <Button
                    size="sm"
                    onClick={() => {
                      const payload = hasPartSelector
                        ? { path: selectedDir, paths: selectedPartPaths }
                        : { path: selectedDir === "__none__" ? "" : selectedDir };
                      triggerSyncFromDir(payload);
                    }}
                    disabled={
                      isSyncingFromDir
                      || syncStatus?.is_syncing
                      || selectedDir === "__none__"
                      || (hasPartSelector && selectedPartPaths.length === 0)
                    }
                    className="gap-1.5"
                  >
                    {isSyncingFromDir || syncStatus?.is_syncing ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Play className="size-3.5" />
                    )}
                    {t.admin.createVideos}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* NotebookLM Auth */}
        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Settings className="size-4" />
              {t.admin.notebookLMAuth}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              className={cn(
                "flex items-center gap-2.5 px-3 py-2.5 rounded-lg border text-sm font-medium",
                authCfg.className
              )}
            >
              <AuthIcon className="size-4 shrink-0" />
              {authCfg.label}
            </div>

            <p className="text-xs text-muted-foreground">
              {t.admin.notebookLMDesc}
            </p>

            {authState !== "authenticated" && (
              <div className="space-y-3">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="gap-1.5 border-primary text-primary hover:bg-primary/5 w-full sm:w-auto"
                  onClick={() => setCredentialModalOpen(true)}
                >
                  <UploadCloud className="size-3.5" />
                  {t.admin.notebookLMSaveCookieButton}
                </Button>
                {process.env.NEXT_PUBLIC_STORAGE_BACKEND !== "gcs" && (
                  <div className="rounded-lg border border-border bg-muted/20 px-3 py-3 space-y-2">
                    <p className="text-xs font-medium text-foreground">{t.admin.adminRemoteLoginTitle}</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{t.admin.adminRemoteLoginNote}</p>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="gap-1.5 border-primary text-primary hover:bg-primary/5 w-full sm:w-auto"
                      onClick={() => setRemoteLoginOpen(true)}
                    >
                      <Monitor className="size-3.5" />
                      Remote Login
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Articles list */}
      <Card className="border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <BookOpen className="size-4" />
            {t.admin.articlesVideos}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {articlesLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
            </div>
          ) : articles.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm text-muted-foreground">{t.admin.noArticles}</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {articles.map((article) => (
                <div key={article.id} className="flex items-center gap-4 px-4 py-3">
                  <div className="size-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
                    <FileText className="size-4 text-muted-foreground/60" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{article.title}</p>
                    <p className="text-xs text-muted-foreground font-mono truncate">{article.gitPath}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {article.categoryName && (
                      <span className="text-xs text-muted-foreground hidden sm:block">{article.categoryName}</span>
                    )}
                    <VideoStatusBadge status={article.latestVideoStatus} t={t} />
                    {article.latestVideoId && article.latestVideoStatus === "ready" && (
                      <a
                        href={`/videos/${article.latestVideoId}`}
                        className="text-xs text-primary hover:underline"
                      >
                        {t.common.view}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <Suspense fallback={null}>
        <UploadSessionModal
          open={credentialModalOpen}
          onClose={() => setCredentialModalOpen(false)}
          onAuthSaved={() => {
            queryClient.invalidateQueries({ queryKey: ["auth-status"] });
            setSyncMessage(
              "NotebookLM認証を保存しました。状態が更新されない場合はGoogleに再ログインしてください。"
            );
          }}
        />
        <RemoteLoginModal
          open={remoteLoginOpen}
          onClose={() => setRemoteLoginOpen(false)}
          onAuthSaved={() => {
            queryClient.invalidateQueries({ queryKey: ["auth-status"] });
            setSyncMessage("NotebookLM認証を保存しました。状態が更新されない場合はGoogleに再ログインしてください。");
          }}
        />
      </Suspense>
    </div>
  );
}
