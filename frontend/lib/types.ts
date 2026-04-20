// ---------------------------------------------------------------------------
// E-learning types
// ---------------------------------------------------------------------------

export interface Video {
  id: string;
  title: string;
  description?: string;
  thumbnailUrl?: string;
  durationSec?: number;
  viewerCount?: number;
  viewCount?: number;
  style?: string;
  status: "generating" | "ready" | "error";
  publishedAt?: string;
  createdAt: string;
  updatedAt: string;
  jobId?: string;
  articleId?: string;
  categoryId?: string;
  categoryName?: string;
  categorySlug?: string;
  watched?: boolean;
  watchLater?: boolean;
  liked?: boolean;
  wikiUrl?: string;
}

/** Request body for PATCH /api/admin/videos/{id} */
export type AdminVideoPatch = {
  title?: string;
  description?: string;
  status?: string;
  thumbnailUrl?: string;
  durationSec?: number;
  publishedAt?: string | null;
  style?: string;
  language?: string;
};

export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string;
  sortOrder: number;
  videoCount: number;
}

export interface User {
  id: string;
  email: string;
  displayName: string;
  createdAt: string;
  isAdmin?: boolean;
}

export interface WatchRecord {
  id: string;
  userId: string;
  videoId: string;
  videoTitle?: string;
  videoStatus?: string;
  categoryName?: string;
  categorySlug?: string;
  completed: boolean;
  watchedAt: string;
}

export interface ArticleRecord {
  id: string;
  title: string;
  gitPath: string;
  gitHash?: string;
  categoryId?: string;
  categoryName?: string;
  latestVideoId?: string;
  latestVideoStatus?: string;
  createdAt: string;
  updatedAt: string;
}

export interface WikiSyncStatus {
  last_sync_at?: string;
  last_hash?: string;
  total_articles: number;
  is_syncing: boolean;
  error?: string;
}

export interface WikiSyncResult {
  status: "success" | "no_changes" | "no_files" | "error" | "skipped" | "already_running";
  message?: string;
  processed?: number;
  jobs_created?: number;
  hash?: string;
}

/** POST /wiki/sync-from-git — バックグラウンド開始の応答 */
export interface WikiGitSyncStart {
  message: string;
  sync_id: string;
}

export interface WikiDirectory {
  path: string;
  label: string;
  count: number;
  files?: Array<{
    fileName: string;
    path: string;
  }>;
}

// ---------------------------------------------------------------------------
// Comment types
// ---------------------------------------------------------------------------

export interface Comment {
  id: string;
  videoId: string;
  userId: string;
  displayName: string;
  text: string;
  likeCount: number;
  likedByMe: boolean;
  createdAt: string;
  parentId?: string;
  replies?: Comment[];
}

export interface CreateCommentRequest {
  text: string;
  parentId?: string;
}

// ---------------------------------------------------------------------------
// Job types (kept for admin/jobs page)
// ---------------------------------------------------------------------------

export type VideoStyle =
  | "auto"
  | "classic"
  | "whiteboard"
  | "kawaii"
  | "anime"
  | "watercolor"
  | "retro-print"
  | "heritage"
  | "paper-craft";

export type VideoFormat = "explainer" | "brief";

export type JobType = "video";

export type JobStatus = "pending" | "processing" | "completed" | "error";

export type JobStep =
  | "create_notebook"
  | "add_source"
  | "generate_video"
  | "wait_completion"
  | "download_ready";

export interface JobStepInfo {
  id: JobStep | string;
  label: string;
  status: "pending" | "in_progress" | "completed" | "error";
  message?: string;
}

export type AuthStatusValue = "authenticated" | "not_logged_in" | "session_expired";

export interface AuthStatus {
  status: AuthStatusValue;
}

export interface Job {
  id: string;
  jobType: JobType;
  csvFileNames: string;
  notebookTitle: string;
  instructions: string;
  style?: VideoStyle;
  format?: VideoFormat;
  language: string;
  timeout: number;
  status: JobStatus;
  steps: JobStepInfo[];
  currentStep?: string;
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
}

export interface JobStats {
  total: number;
  processing: number;
  completed: number;
  error: number;
}

export interface ApiInfo {
  base_url: string;
  api_keys: string[];
  has_keys: boolean;
}

export const VIDEO_STYLE_LABELS: Record<VideoStyle, { label: string; description: string }> = {
  auto: { label: "自動選択", description: "AIが最適なスタイルを自動選択" },
  classic: { label: "クラシック", description: "シンプルで落ち着いたスタイル" },
  whiteboard: { label: "ホワイトボード", description: "ホワイトボード風の手書き表現" },
  kawaii: { label: "かわいい", description: "かわいらしいイラストスタイル" },
  anime: { label: "アニメ", description: "日本のアニメ風スタイル" },
  watercolor: { label: "水彩画", description: "柔らかい水彩画風表現" },
  "retro-print": { label: "レトロプリント", description: "レトロな印刷物風スタイル" },
  heritage: { label: "ヘリテージ", description: "クラシックな伝統的スタイル" },
  "paper-craft": { label: "ペーパークラフト", description: "紙工作風の温かみのある表現" },
};

export const JOB_STEP_LABELS: Record<JobStep, string> = {
  create_notebook: "ノートブック作成",
  add_source: "ドキュメント追加",
  generate_video: "動画生成開始",
  wait_completion: "生成完了待機",
  download_ready: "ダウンロード準備完了",
};
