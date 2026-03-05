import type { ApiInfo, AuthStatus, CreateAudioJobPayload, CreateJobPayload, Job, JobStats } from "./types";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_JOBS: Job[] = [
  {
    id: "job_001",
    jobType: "video",
    csvFileNames: "安全運転一覧_埼玉営業所（車両毎）_202601_.csv",
    notebookTitle: "安全運転レポート 202601",
    instructions: "CSVデータの主要な傾向と示唆を分かりやすく解説してください",
    style: "whiteboard",
    format: "explainer",
    language: "ja",
    timeout: 1800,
    status: "completed",
    steps: [
      { id: "create_notebook", label: "ノートブック作成", status: "completed" },
      { id: "add_source", label: "CSVソース追加", status: "completed" },
      { id: "generate_video", label: "動画生成開始", status: "completed" },
      { id: "wait_completion", label: "生成完了待機", status: "completed" },
      { id: "download_ready", label: "ダウンロード準備完了", status: "completed" },
    ],
    currentStep: "download_ready",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    completedAt: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
  },
  {
    id: "job_002",
    jobType: "video",
    csvFileNames: "走行管理一覧_埼玉営業所（車両毎）_202601_.csv",
    notebookTitle: "走行管理レポート 202601",
    instructions: "走行距離と燃費の傾向を詳しく解説してください",
    style: "classic",
    format: "brief",
    language: "ja",
    timeout: 1800,
    status: "processing",
    steps: [
      { id: "create_notebook", label: "ノートブック作成", status: "completed" },
      { id: "add_source", label: "CSVソース追加", status: "completed" },
      { id: "generate_video", label: "動画生成開始", status: "completed" },
      { id: "wait_completion", label: "生成完了待機", status: "in_progress", message: "動画を生成中... (約5分)" },
      { id: "download_ready", label: "ダウンロード準備完了", status: "pending" },
    ],
    currentStep: "wait_completion",
    createdAt: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
  },
  {
    id: "job_003",
    jobType: "video",
    csvFileNames: "バック一覧_埼玉営業所（車両毎）_202601_.csv",
    notebookTitle: "バック動作分析 202601",
    instructions: "バック回数と速度超過の関連性を分析してください",
    style: "anime",
    format: "explainer",
    language: "ja",
    timeout: 1800,
    status: "error",
    steps: [
      { id: "create_notebook", label: "ノートブック作成", status: "completed" },
      { id: "add_source", label: "CSVソース追加", status: "error", message: "ファイルのインデックス作成がタイムアウトしました" },
      { id: "generate_video", label: "動画生成開始", status: "pending" },
      { id: "wait_completion", label: "生成完了待機", status: "pending" },
      { id: "download_ready", label: "ダウンロード準備完了", status: "pending" },
    ],
    currentStep: "add_source",
    errorMessage: "ソースのインデックス作成がタイムアウトしました。CSVファイルのサイズを確認してください。",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
  },
  {
    id: "job_004",
    jobType: "audio",
    csvFileNames: "安全運転一覧_埼玉営業所（車両毎）_202601_.csv",
    notebookTitle: "安全運転レポート 音声解説",
    instructions: "CSVデータの主要な傾向と示唆を分かりやすく解説してください",
    language: "ja",
    timeout: 600,
    status: "completed",
    voiceName: "Kore",
    generatedScript: "今月の安全運転レポートをご説明します。今月は全体的に安全スコアが改善され...",
    steps: [
      { id: "read_csv", label: "CSV読み込み", status: "completed" },
      { id: "generate_script", label: "解説原稿生成", status: "completed" },
      { id: "generate_audio", label: "音声生成", status: "completed" },
      { id: "download_ready", label: "ダウンロード準備完了", status: "completed" },
    ],
    currentStep: "download_ready",
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
    completedAt: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
  },
];

// ---------------------------------------------------------------------------
// Mock implementations
// ---------------------------------------------------------------------------

async function mockDelay(ms = 400) {
  await new Promise((res) => setTimeout(res, ms));
}

async function mockGetStats(): Promise<JobStats> {
  await mockDelay();
  return {
    total: MOCK_JOBS.length,
    processing: MOCK_JOBS.filter((j) => j.status === "processing").length,
    completed: MOCK_JOBS.filter((j) => j.status === "completed").length,
    error: MOCK_JOBS.filter((j) => j.status === "error").length,
  };
}

async function mockGetJobs(status?: string, type?: string): Promise<Job[]> {
  await mockDelay();
  let jobs = MOCK_JOBS;
  if (status && status !== "all") jobs = jobs.filter((j) => j.status === status);
  if (type && type !== "all") jobs = jobs.filter((j) => j.jobType === type);
  return jobs;
}

async function mockGetJob(id: string): Promise<Job> {
  await mockDelay();
  const job = MOCK_JOBS.find((j) => j.id === id);
  if (!job) throw new Error(`ジョブが見つかりません: ${id}`);
  return job;
}

async function mockCreateJob(payload: CreateJobPayload): Promise<Job> {
  await mockDelay(800);
  const newJob: Job = {
    id: `job_${Date.now()}`,
    jobType: "video",
    csvFileNames: payload.csvFiles.map((f) => f.name).join(","),
    notebookTitle: payload.notebookTitle,
    instructions: payload.instructions,
    style: payload.style,
    format: payload.format,
    language: payload.language,
    timeout: payload.timeout,
    status: "pending",
    steps: [
      { id: "create_notebook", label: "ノートブック作成", status: "pending" },
      { id: "add_source", label: "CSVソース追加", status: "pending" },
      { id: "generate_video", label: "動画生成開始", status: "pending" },
      { id: "wait_completion", label: "生成完了待機", status: "pending" },
      { id: "download_ready", label: "ダウンロード準備完了", status: "pending" },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  MOCK_JOBS.unshift(newJob);
  return newJob;
}

async function mockCreateAudioJob(payload: CreateAudioJobPayload): Promise<Job> {
  await mockDelay(800);
  const newJob: Job = {
    id: `job_${Date.now()}`,
    jobType: "audio",
    csvFileNames: payload.csvFiles.map((f) => f.name).join(","),
    notebookTitle: payload.title,
    instructions: payload.instructions,
    language: payload.language,
    timeout: payload.timeout,
    voiceName: payload.voiceName,
    status: "pending",
    steps: [
      { id: "read_csv", label: "CSV読み込み", status: "pending" },
      { id: "generate_script", label: "解説原稿生成", status: "pending" },
      { id: "generate_audio", label: "音声生成", status: "pending" },
      { id: "download_ready", label: "ダウンロード準備完了", status: "pending" },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  MOCK_JOBS.unshift(newJob);
  return newJob;
}

// ---------------------------------------------------------------------------
// Real API implementations
// ---------------------------------------------------------------------------

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

async function realGetStats(): Promise<JobStats> {
  const res = await fetch(`${BASE_URL}/jobs/stats`);
  if (!res.ok) throw new Error("統計情報の取得に失敗しました");
  return res.json();
}

async function realGetJobs(status?: string, type?: string): Promise<Job[]> {
  const params = new URLSearchParams();
  if (status && status !== "all") params.set("status", status);
  if (type && type !== "all") params.set("type", type);
  const query = params.toString();
  const url = query ? `${BASE_URL}/jobs?${query}` : `${BASE_URL}/jobs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("ジョブ一覧の取得に失敗しました");
  return res.json();
}

async function realGetJob(id: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/jobs/${id}`);
  if (!res.ok) throw new Error(`ジョブの取得に失敗しました: ${id}`);
  return res.json();
}

async function realCreateJob(payload: CreateJobPayload): Promise<Job> {
  const formData = new FormData();
  for (const file of payload.csvFiles) {
    formData.append("csvFiles", file);
  }
  formData.append("notebookTitle", payload.notebookTitle);
  formData.append("instructions", payload.instructions);
  formData.append("style", payload.style);
  formData.append("format", payload.format);
  formData.append("language", payload.language);
  formData.append("timeout", String(payload.timeout));

  const res = await fetch(`${BASE_URL}/jobs`, { method: "POST", body: formData });
  if (!res.ok) throw new Error("ジョブの作成に失敗しました");
  return res.json();
}

async function realCreateAudioJob(payload: CreateAudioJobPayload): Promise<Job> {
  const formData = new FormData();
  for (const file of payload.csvFiles) {
    formData.append("csvFiles", file);
  }
  formData.append("title", payload.title);
  formData.append("instructions", payload.instructions);
  formData.append("voiceName", payload.voiceName);
  formData.append("language", payload.language);
  formData.append("timeout", String(payload.timeout));
  formData.append("stylePrompt", payload.stylePrompt);

  const res = await fetch(`${BASE_URL}/audio-jobs`, { method: "POST", body: formData });
  if (!res.ok) throw new Error("音声ジョブの作成に失敗しました");
  return res.json();
}

async function realGetAuthStatus(): Promise<AuthStatus> {
  const res = await fetch(`${BASE_URL}/auth/status`);
  if (!res.ok) throw new Error("認証状態の取得に失敗しました");
  return res.json();
}

async function realTriggerLogin(): Promise<{ message: string }> {
  const res = await fetch(`${BASE_URL}/auth/login`, { method: "POST" });
  if (!res.ok) throw new Error("ログイン起動に失敗しました");
  return res.json();
}

async function mockGetAuthStatus(): Promise<AuthStatus> {
  await mockDelay();
  return { status: "authenticated" };
}

async function mockTriggerLogin(): Promise<{ message: string }> {
  await mockDelay(500);
  return { message: "モック: ログインブラウザを開きました。" };
}

async function mockGetApiInfo(): Promise<ApiInfo> {
  await mockDelay();
  return {
    base_url: "http://localhost:8000/api/v1",
    api_keys: ["local-te***key"],
    has_keys: true,
  };
}

async function realGetApiInfo(): Promise<ApiInfo> {
  const res = await fetch(`${BASE_URL}/settings/api-info`);
  if (!res.ok) throw new Error("API情報の取得に失敗しました");
  return res.json();
}

// ---------------------------------------------------------------------------
// Exported API client
// ---------------------------------------------------------------------------

export const api = {
  getStats: USE_MOCK ? mockGetStats : realGetStats,
  getJobs: USE_MOCK ? mockGetJobs : realGetJobs,
  getJob: USE_MOCK ? mockGetJob : realGetJob,
  createJob: USE_MOCK ? mockCreateJob : realCreateJob,
  createAudioJob: USE_MOCK ? mockCreateAudioJob : realCreateAudioJob,
  getAuthStatus: USE_MOCK ? mockGetAuthStatus : realGetAuthStatus,
  triggerLogin: USE_MOCK ? mockTriggerLogin : realTriggerLogin,

  getApiInfo: USE_MOCK ? mockGetApiInfo : realGetApiInfo,

  getDownloadUrl(id: string): string {
    return `${BASE_URL}/jobs/${id}/download`;
  },
};
