import type {
  ApiInfo,
  AuthStatus,
  Category,
  Comment,
  CreateCommentRequest,
  Job,
  JobStats,
  User,
  Video,
  WatchRecord,
  WikiSyncResult,
  WikiSyncStatus,
  WikiGitSyncStart,
  WikiDirectory,
  ArticleRecord,
  AdminVideoPatch,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

function getUserId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("user_id");
}

// ---------------------------------------------------------------------------
// Real API implementations
// ---------------------------------------------------------------------------

function getHeaders(): HeadersInit {
  const userId = getUserId();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (userId) headers["x-user-id"] = userId;
  return headers;
}

function getFetchHeaders(): HeadersInit {
  const userId = getUserId();
  if (userId) return { "x-user-id": userId };
  return {};
}

/** Backend の require_admin_user 等は x-user-id または Cookie user_id が必要。GitHub の access token は送らない。 */
function withUserAuth(init: RequestInit = {}): RequestInit {
  const { headers: h, ...rest } = init;
  const merged: Record<string, string> = {
    ...(getFetchHeaders() as Record<string, string>),
  };
  if (h && typeof h === "object" && !(h instanceof Headers)) {
    Object.assign(merged, h as Record<string, string>);
  }
  return {
    ...rest,
    credentials: "include",
    headers: merged,
  };
}

async function realGetCategories(params?: { locale?: string }): Promise<Category[]> {
  const p = new URLSearchParams();
  if (params?.locale) p.set("locale", params.locale);
  const query = p.toString();
  const url = query ? `${BASE_URL}/categories?${query}` : `${BASE_URL}/categories`;
  const res = await fetch(url, { headers: getFetchHeaders() });
  if (!res.ok) throw new Error("カテゴリの取得に失敗しました");
  return res.json();
}

async function realGetVideos(params?: {
  category?: string;
  search?: string;
  status?: string;
  limit?: number;
  offset?: number;
  locale?: string;
  publishedAfter?: string;
}): Promise<Video[]> {
  const p = new URLSearchParams();
  if (params?.category) p.set("category", params.category);
  if (params?.search) p.set("search", params.search);
  if (params?.status) p.set("status", params.status);
  if (params?.limit) p.set("limit", String(params.limit));
  if (params?.offset) p.set("offset", String(params.offset));
  if (params?.locale) p.set("locale", params.locale);
  if (params?.publishedAfter) p.set("published_after", params.publishedAfter);
  const query = p.toString();
  const url = query ? `${BASE_URL}/videos?${query}` : `${BASE_URL}/videos`;
  const res = await fetch(url, { headers: getFetchHeaders() });
  if (!res.ok) throw new Error("動画一覧の取得に失敗しました");
  return res.json();
}

async function realGetVideo(id: string): Promise<Video> {
  const res = await fetch(`${BASE_URL}/videos/${id}`, { headers: getFetchHeaders() });
  if (!res.ok) throw new Error(`動画の取得に失敗しました: ${id}`);
  return res.json();
}

async function realRecordWatch(videoId: string, completed = true): Promise<void> {
  const userId = getUserId();
  if (!userId) {
    throw new Error("ログインが必要です");
  }
  const res = await fetch(`${BASE_URL}/videos/${videoId}/watch`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-user-id": userId },
    body: JSON.stringify({ completed }),
  });
  if (!res.ok) throw new Error("視聴記録の保存に失敗しました");
}

async function realGetWatchHistory(): Promise<WatchRecord[]> {
  const res = await fetch(`${BASE_URL}/users/me/history`, { headers: getFetchHeaders() });
  if (!res.ok) throw new Error("視聴履歴の取得に失敗しました");
  return res.json();
}

async function realToggleWatchLater(videoId: string): Promise<{ added: boolean }> {
  const res = await fetch(`${BASE_URL}/videos/${videoId}/watch-later`, {
    method: "POST",
    headers: getFetchHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw new Error("後で見るの登録に失敗しました");
  const data = await res.json();
  return { added: data.added };
}

async function realToggleLiked(videoId: string): Promise<{ added: boolean }> {
  const res = await fetch(`${BASE_URL}/videos/${videoId}/liked`, {
    method: "POST",
    headers: getFetchHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw new Error("高く評価の登録に失敗しました");
  const data = await res.json();
  return { added: data.added };
}

async function realGetWatchLater(): Promise<Video[]> {
  const res = await fetch(`${BASE_URL}/users/me/watch-later`, { headers: getFetchHeaders() });
  if (!res.ok) throw new Error("後で見るの取得に失敗しました");
  return res.json();
}

async function realGetLikedVideos(): Promise<Video[]> {
  const res = await fetch(`${BASE_URL}/users/me/liked`, { headers: getFetchHeaders() });
  if (!res.ok) throw new Error("高く評価した動画の取得に失敗しました");
  return res.json();
}

async function realUserLogin(email: string, displayName: string): Promise<User> {
  const res = await fetch(`${BASE_URL}/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, displayName }),
    credentials: "include",
  });
  if (!res.ok) throw new Error("ログインに失敗しました");
  const user: User = await res.json();
  if (typeof window !== "undefined") {
    localStorage.setItem("user_id", user.id);
    localStorage.setItem("user_email", user.email);
    localStorage.setItem("user_display_name", user.displayName);
  }
  return user;
}

async function realGetCurrentUser(): Promise<User | null> {
  try {
    const res = await fetch(`${BASE_URL}/users/me`, { headers: getFetchHeaders(), credentials: "include" });
    if (!res.ok) return null;
    const raw = await res.json();
    if (raw === null || typeof raw !== "object") return null;
    const data = raw as Record<string, unknown>;
    const id = data.id as string;
    const email = data.email as string;
    const displayName = (data.displayName ?? data.display_name ?? "") as string;
    const createdAt = (data.createdAt ?? data.created_at ?? "") as string;
    const isAdmin = Boolean(data.isAdmin ?? data.is_admin);
    if (!id || !email) return null;
    return { id, email, displayName, createdAt, isAdmin };
  } catch {
    return null;
  }
}

async function realGetStats(): Promise<JobStats> {
  const res = await fetch(`${BASE_URL}/jobs/stats`, withUserAuth());
  if (!res.ok) throw new Error("統計情報の取得に失敗しました");
  return res.json();
}

async function realGetJobs(status?: string): Promise<Job[]> {
  const p = new URLSearchParams();
  if (status && status !== "all") p.set("status", status);
  const url = p.toString() ? `${BASE_URL}/jobs?${p}` : `${BASE_URL}/jobs`;
  const res = await fetch(url, withUserAuth());
  if (!res.ok) throw new Error("ジョブ一覧の取得に失敗しました");
  return res.json();
}

async function realGetJob(id: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/jobs/${id}`, withUserAuth());
  if (!res.ok) throw new Error(`ジョブの取得に失敗しました: ${id}`);
  return res.json();
}

async function realGetAuthStatus(): Promise<AuthStatus> {
  const res = await fetch(`${BASE_URL}/auth/status`, withUserAuth());
  if (!res.ok) throw new Error("認証状態の取得に失敗しました");
  return res.json();
}

async function realTriggerLogin(): Promise<{ message: string }> {
  const res = await fetch(
    `${BASE_URL}/auth/login`,
    withUserAuth({ method: "POST", headers: { "Content-Type": "application/json" } }),
  );
  if (!res.ok) throw new Error("ログイン起動に失敗しました");
  return res.json();
}

async function realGetApiInfo(): Promise<ApiInfo> {
  const res = await fetch(`${BASE_URL}/settings/api-info`, withUserAuth());
  if (!res.ok) throw new Error("API情報の取得に失敗しました");
  return res.json();
}

async function realUploadNotebookLMSession(sessionJson: string): Promise<{ message: string }> {
  const res = await fetch(`${BASE_URL}/auth/upload-session`, {
    method: "POST",
    headers: getHeaders() as Record<string, string>,
    body: JSON.stringify({ session_json: sessionJson }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "セッションのアップロードに失敗しました");
  }
  return res.json();
}

async function realGetWikiSyncStatus(): Promise<WikiSyncStatus> {
  const res = await fetch(`${BASE_URL}/wiki/sync-status`, withUserAuth());
  if (!res.ok) throw new Error("Wiki同期状態の取得に失敗しました");
  return res.json();
}

async function realGetAdminArticles(): Promise<ArticleRecord[]> {
  const res = await fetch(`${BASE_URL}/admin/articles`, withUserAuth());
  if (!res.ok) throw new Error("記事一覧の取得に失敗しました");
  return res.json();
}

async function realGetAdminVideos(params?: {
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<Video[]> {
  const p = new URLSearchParams();
  if (params?.search) p.set("search", params.search);
  if (params?.limit != null) p.set("limit", String(params.limit));
  if (params?.offset != null) p.set("offset", String(params.offset));
  const query = p.toString();
  const url = query ? `${BASE_URL}/admin/videos?${query}` : `${BASE_URL}/admin/videos`;
  const res = await fetch(url, withUserAuth());
  if (!res.ok) throw new Error("管理用動画一覧の取得に失敗しました");
  return res.json();
}

async function realPatchAdminVideo(id: string, body: AdminVideoPatch): Promise<Video> {
  const res = await fetch(`${BASE_URL}/admin/videos/${id}`, withUserAuth({
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }));
  if (!res.ok) throw new Error("動画の更新に失敗しました");
  return res.json();
}

async function realDeleteAdminVideo(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/admin/videos/${id}`, withUserAuth({ method: "DELETE" }));
  if (!res.ok) throw new Error("動画の削除に失敗しました");
}

async function realGetWikiDirectories(): Promise<WikiDirectory[]> {
  const res = await fetch(`${BASE_URL}/wiki/directories`, withUserAuth());
  if (!res.ok) throw new Error("ディレクトリ一覧の取得に失敗しました");
  return res.json();
}

async function realTriggerWikiSyncFromDirectory(payload: { path?: string; paths?: string[] }): Promise<WikiSyncResult> {
  const res = await fetch(
    `${BASE_URL}/wiki/sync-directory`,
    withUserAuth({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
  if (!res.ok) throw new Error("ディレクトリの動画作成の開始に失敗しました");
  return res.json();
}

async function realTriggerWikiSyncFromGit(): Promise<WikiGitSyncStart> {
  const res = await fetch(
    `${BASE_URL}/wiki/sync-from-git`,
    withUserAuth({ method: "POST" }),
  );
  if (!res.ok) throw new Error("Wiki の Git 同期の開始に失敗しました");
  return res.json();
}


async function realGetComments(videoId: string): Promise<Comment[]> {
  const res = await fetch(`${BASE_URL}/videos/${videoId}/comments`, {
    headers: getFetchHeaders(),
  });
  if (!res.ok) throw new Error("コメントの取得に失敗しました");
  return res.json();
}

async function realCreateComment(videoId: string, req: CreateCommentRequest): Promise<Comment> {
  const res = await fetch(`${BASE_URL}/videos/${videoId}/comments`, {
    method: "POST",
    headers: getHeaders() as Record<string, string>,
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("コメントの投稿に失敗しました");
  return res.json();
}

async function realToggleCommentLike(commentId: string): Promise<Comment> {
  const res = await fetch(`${BASE_URL}/comments/${commentId}/like`, {
    method: "POST",
    headers: getFetchHeaders(),
  });
  if (!res.ok) throw new Error("いいねに失敗しました");
  return res.json();
}


// ---------------------------------------------------------------------------
// Exported API client
// ---------------------------------------------------------------------------

export const api = {
  getCategories: realGetCategories,
  getVideos: realGetVideos,
  getVideo: realGetVideo,
  recordWatch: realRecordWatch,
  getWatchHistory: realGetWatchHistory,
  toggleWatchLater: realToggleWatchLater,
  toggleLiked: realToggleLiked,
  getWatchLater: realGetWatchLater,
  getLikedVideos: realGetLikedVideos,
  userLogin: realUserLogin,
  getCurrentUser: realGetCurrentUser,

  getWikiSyncStatus: realGetWikiSyncStatus,
  getWikiDirectories: realGetWikiDirectories,
  triggerWikiSyncFromDirectory: realTriggerWikiSyncFromDirectory,
  triggerWikiSyncFromGit: realTriggerWikiSyncFromGit,
  getAdminArticles: realGetAdminArticles,
  getAdminVideos: realGetAdminVideos,
  patchAdminVideo: realPatchAdminVideo,
  deleteAdminVideo: realDeleteAdminVideo,

  getStats: realGetStats,
  getJobs: realGetJobs,
  getJob: realGetJob,

  getAuthStatus: realGetAuthStatus,
  triggerLogin: realTriggerLogin,
  uploadNotebookLMSession: realUploadNotebookLMSession,
  getApiInfo: realGetApiInfo,

  getComments: realGetComments,
  createComment: realCreateComment,
  toggleCommentLike: realToggleCommentLike,

  getVideoStreamUrl(id: string, _jobId: string): string {
    return `${BASE_URL}/videos/${id}/stream`;
  },

  getDownloadUrl(jobId: string): string {
    return `${BASE_URL}/jobs/${jobId}/download`;
  },
};

