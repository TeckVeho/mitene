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

export type JobStatus = "pending" | "processing" | "completed" | "error";

export type JobStep =
  | "create_notebook"
  | "add_source"
  | "generate_video"
  | "wait_completion"
  | "download_ready";

export interface JobStepInfo {
  id: JobStep;
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
  csvFileNames: string; // カンマ区切りのファイル名リスト
  notebookTitle: string;
  instructions: string;
  style: VideoStyle;
  format: VideoFormat;
  language: string;
  timeout: number;
  status: JobStatus;
  steps: JobStepInfo[];
  currentStep?: JobStep;
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

export interface CreateJobPayload {
  csvFiles: File[];
  notebookTitle: string;
  instructions: string;
  style: VideoStyle;
  format: VideoFormat;
  language: string;
  timeout: number;
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
  add_source: "CSVソース追加",
  generate_video: "動画生成開始",
  wait_completion: "生成完了待機",
  download_ready: "ダウンロード準備完了",
};
