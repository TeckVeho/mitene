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
  WikiDirectory,
  ArticleRecord,
} from "./types";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_CATEGORIES: Category[] = [
  { id: "cat_001", name: "セキュリティ", slug: "security", description: "情報セキュリティに関する社内ルール", sortOrder: 1, videoCount: 5 },
  { id: "cat_002", name: "開発規約", slug: "development", description: "コーディング規約・開発プロセス", sortOrder: 2, videoCount: 4 },
  { id: "cat_003", name: "インフラ", slug: "infrastructure", description: "インフラ・クラウド運用ルール", sortOrder: 3, videoCount: 4 },
  { id: "cat_004", name: "コミュニケーション", slug: "communication", description: "チームコミュニケーションルール", sortOrder: 4, videoCount: 2 },
  { id: "cat_005", name: "その他", slug: "misc", description: "その他の社内ルール", sortOrder: 99, videoCount: 1 },
];

const MOCK_VIDEOS: Video[] = [
  {
    id: "vid_001",
    title: "GitHubセキュリティ運用ガイドライン",
    description: "GitHub利用時のセキュリティルール・2FAの設定・アクセストークン管理について解説します。",
    thumbnailUrl: "https://picsum.photos/seed/github-sec/480/270",
    durationSec: 183,
    viewerCount: 1205,
    viewCount: 1842,
    style: "whiteboard",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
    jobId: "job_sample_001",
    categoryId: "cat_001",
    categoryName: "セキュリティ",
    categorySlug: "security",
    watched: false,
    wikiUrl: "https://github.com/your-org/wiki/blob/main/security/github-security.md",
  },
  {
    id: "vid_002",
    title: "コードレビュー規約 - 品質向上のためのPR作成ガイド",
    description: "品質の高いコードを維持するためのレビュープロセスと基準を解説します。Pull Requestの書き方から承認フローまで。",
    thumbnailUrl: "https://picsum.photos/seed/codereview/480/270",
    durationSec: 247,
    viewerCount: 2103,
    viewCount: 3241,
    style: "classic",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    jobId: "job_sample_002",
    categoryId: "cat_002",
    categoryName: "開発規約",
    categorySlug: "development",
    watched: true,
    wikiUrl: "https://github.com/your-org/wiki/blob/main/development/code-review.md",
  },
  {
    id: "vid_003",
    title: "AWSリソース命名規則 完全ガイド",
    description: "統一したAWSリソース命名規則の定義と実例を解説します。S3、EC2、RDSなど主要サービスの命名パターン。",
    thumbnailUrl: "https://picsum.photos/seed/aws-naming/480/270",
    durationSec: 312,
    viewerCount: 756,
    viewCount: 987,
    style: "whiteboard",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 6).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
    jobId: "job_sample_003",
    categoryId: "cat_003",
    categoryName: "インフラ",
    categorySlug: "infrastructure",
    watched: false,
    wikiUrl: "https://github.com/your-org/wiki/blob/main/infrastructure/aws-naming.md",
  },
  {
    id: "vid_004",
    title: "Slackコミュニケーションガイドライン",
    description: "チームでのSlack利用ルール、チャンネル命名規則、絵文字リアクション文化について解説します。",
    thumbnailUrl: "https://picsum.photos/seed/slack-guide/480/270",
    durationSec: 198,
    viewerCount: 1689,
    viewCount: 2156,
    style: "anime",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 50).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
    jobId: "job_sample_004",
    categoryId: "cat_004",
    categoryName: "コミュニケーション",
    categorySlug: "communication",
    watched: false,
  },
  {
    id: "vid_005",
    title: "インシデント対応フロー - 障害時の初動対応マニュアル",
    description: "本番障害発生時の初動対応から復旧・振り返りまでの標準フローを解説します。",
    thumbnailUrl: "https://picsum.photos/seed/incident/480/270",
    durationSec: 328,
    viewerCount: 3205,
    viewCount: 4521,
    style: "whiteboard",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 75).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
    jobId: "job_sample_005",
    categoryId: "cat_001",
    categoryName: "セキュリティ",
    categorySlug: "security",
    watched: true,
  },
  {
    id: "vid_006",
    title: "Dockerコンテナ運用ベストプラクティス",
    description: "本番環境でのDocker運用における注意点とベストプラクティスを解説。Dockerfile最適化からセキュリティまで。",
    thumbnailUrl: "https://picsum.photos/seed/docker-ops/480/270",
    durationSec: 421,
    viewerCount: 1456,
    viewCount: 1893,
    style: "whiteboard",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
    jobId: "job_sample_006",
    categoryId: "cat_003",
    categoryName: "インフラ",
    categorySlug: "infrastructure",
    watched: false,
  },
  {
    id: "vid_007",
    title: "GitブランチStrategyとリリースフロー",
    description: "Git-flow、GitHub-flow、trunk-basedの比較と社内採用ブランチ戦略を解説します。",
    thumbnailUrl: "https://picsum.photos/seed/git-branch/480/270",
    durationSec: 356,
    viewerCount: 1987,
    viewCount: 2734,
    style: "classic",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 8).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
    jobId: "job_sample_007",
    categoryId: "cat_002",
    categoryName: "開発規約",
    categorySlug: "development",
    watched: true,
  },
  {
    id: "vid_008",
    title: "個人情報保護・情報セキュリティ研修 2024年度版",
    description: "個人情報保護法の改正ポイントと社内での適切な情報取り扱いルールを解説します。",
    thumbnailUrl: "https://picsum.photos/seed/privacy-sec/480/270",
    durationSec: 612,
    viewerCount: 6543,
    viewCount: 8921,
    style: "whiteboard",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 31).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
    jobId: "job_sample_008",
    categoryId: "cat_001",
    categoryName: "セキュリティ",
    categorySlug: "security",
    watched: true,
  },
  {
    id: "vid_009",
    title: "CI/CDパイプライン設計と運用ガイド",
    description: "GitHub ActionsとAWS CodePipelineを使ったCI/CDパイプラインの設計から運用まで解説します。",
    thumbnailUrl: "https://picsum.photos/seed/cicd-pipeline/480/270",
    durationSec: 534,
    viewerCount: 1234,
    viewCount: 1654,
    style: "whiteboard",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 11).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
    jobId: "job_sample_009",
    categoryId: "cat_003",
    categoryName: "インフラ",
    categorySlug: "infrastructure",
    watched: false,
  },
  {
    id: "vid_010",
    title: "効果的なMTG運営術 - ファシリテーション入門",
    description: "会議の生産性を高めるファシリテーション技術、アジェンダ設定、意思決定プロセスを解説。",
    thumbnailUrl: "https://picsum.photos/seed/meeting-guide/480/270",
    durationSec: 287,
    viewerCount: 2345,
    viewCount: 3102,
    style: "anime",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 15).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString(),
    jobId: "job_sample_010",
    categoryId: "cat_004",
    categoryName: "コミュニケーション",
    categorySlug: "communication",
    watched: false,
  },
  {
    id: "vid_011",
    title: "テスト駆動開発（TDD）実践ガイド",
    description: "ユニットテスト・統合テストの書き方からカバレッジ目標まで、TDDの実践方法を解説します。",
    thumbnailUrl: "https://picsum.photos/seed/tdd-guide/480/270",
    durationSec: 478,
    viewerCount: 1789,
    viewCount: 2345,
    style: "classic",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 21).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 22).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 21).toISOString(),
    jobId: "job_sample_011",
    categoryId: "cat_002",
    categoryName: "開発規約",
    categorySlug: "development",
    watched: false,
  },
  {
    id: "vid_012",
    title: "ゼロトラストセキュリティ入門",
    description: "ゼロトラストモデルの概念から社内ネットワーク設計への適用方法まで基礎から解説します。",
    thumbnailUrl: "https://picsum.photos/seed/zerotrust/480/270",
    durationSec: 723,
    viewerCount: 4123,
    viewCount: 5678,
    style: "whiteboard",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 60).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 61).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 60).toISOString(),
    jobId: "job_sample_012",
    categoryId: "cat_001",
    categoryName: "セキュリティ",
    categorySlug: "security",
    watched: false,
  },
  {
    id: "vid_013",
    title: "Kubernetes リソース管理と運用監視",
    description: "本番KubernetesクラスターのリソースLimit設定・HPA・PodDisruptionBudgetの設定方法を解説。",
    thumbnailUrl: "https://picsum.photos/seed/k8s-resource/480/270",
    durationSec: 865,
    viewerCount: 987,
    viewCount: 1234,
    style: "whiteboard",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 45).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 46).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 45).toISOString(),
    jobId: "job_sample_013",
    categoryId: "cat_003",
    categoryName: "インフラ",
    categorySlug: "infrastructure",
    watched: false,
  },
  {
    id: "vid_014",
    title: "コード品質管理 - SonarQubeとLintルール設定",
    description: "静的解析ツールの導入からカスタムルール設定まで、コード品質を継続的に維持する方法を解説。",
    thumbnailUrl: "https://picsum.photos/seed/code-quality/480/270",
    durationSec: 391,
    viewerCount: 654,
    viewCount: 892,
    style: "classic",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 18).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 19).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 18).toISOString(),
    jobId: "job_sample_014",
    categoryId: "cat_002",
    categoryName: "開発規約",
    categorySlug: "development",
    watched: false,
  },
  {
    id: "vid_015",
    title: "社内技術ドキュメント作成ガイドライン",
    description: "読みやすい技術ドキュメントの書き方、Markdownのスタイルガイド、図解の活用方法を解説します。",
    thumbnailUrl: "https://picsum.photos/seed/doc-guide/480/270",
    durationSec: 264,
    viewerCount: 2567,
    viewCount: 3456,
    style: "anime",
    status: "ready",
    publishedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 25).toISOString(),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 26).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 25).toISOString(),
    jobId: "job_sample_015",
    categoryId: "cat_005",
    categoryName: "その他",
    categorySlug: "misc",
    watched: false,
  },
  {
    id: "vid_016",
    title: "セキュリティインシデント報告書の書き方",
    description: "セキュリティインシデント発生時の報告書作成フォーマットと記載事項を具体例で解説します。",
    thumbnailUrl: "https://picsum.photos/seed/sec-report/480/270",
    durationSec: 210,
    viewerCount: 543,
    viewCount: 765,
    style: "whiteboard",
    status: "generating",
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    jobId: "job_sample_016",
    categoryId: "cat_001",
    categoryName: "セキュリティ",
    categorySlug: "security",
    watched: false,
  },
];

const MOCK_JOBS: Job[] = [
  {
    id: "job_sample_001",
    jobType: "video",
    csvFileNames: "github-security.md",
    notebookTitle: "GitHubセキュリティ運用ガイドライン",
    instructions: "GitHub利用時のセキュリティルールをわかりやすく解説してください",
    style: "whiteboard",
    format: "explainer",
    language: "ja",
    timeout: 1800,
    status: "completed",
    steps: [
      { id: "create_notebook", label: "ノートブック作成", status: "completed" },
      { id: "add_source", label: "ドキュメント追加", status: "completed" },
      { id: "generate_video", label: "動画生成開始", status: "completed" },
      { id: "wait_completion", label: "生成完了待機", status: "completed" },
      { id: "download_ready", label: "ダウンロード準備完了", status: "completed" },
    ],
    currentStep: "download_ready",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    completedAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
  },
  {
    id: "job_sample_003",
    jobType: "video",
    csvFileNames: "aws-naming.md",
    notebookTitle: "AWSリソース命名規則",
    instructions: "AWSリソース命名規則をわかりやすく解説してください",
    style: "whiteboard",
    format: "explainer",
    language: "ja",
    timeout: 1800,
    status: "processing",
    steps: [
      { id: "create_notebook", label: "ノートブック作成", status: "completed" },
      { id: "add_source", label: "ドキュメント追加", status: "completed" },
      { id: "generate_video", label: "動画生成開始", status: "completed" },
      { id: "wait_completion", label: "生成完了待機", status: "in_progress", message: "動画を生成中... (約5分)" },
      { id: "download_ready", label: "ダウンロード準備完了", status: "pending" },
    ],
    currentStep: "wait_completion",
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
  },
];

const MOCK_USERS: User[] = [
  { id: "user_001", email: "engineer@example.com", displayName: "田中 太郎", createdAt: new Date().toISOString() },
];

let _mockCurrentUser: User | null = null;

const MOCK_WATCH_HISTORY: WatchRecord[] = [
  {
    id: "wh_001",
    userId: "user_001",
    videoId: "vid_002",
    videoTitle: "コードレビュー規約",
    categoryName: "開発規約",
    categorySlug: "development",
    completed: true,
    watchedAt: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
  },
  {
    id: "wh_002",
    userId: "user_001",
    videoId: "vid_005",
    videoTitle: "インシデント対応フロー",
    categoryName: "セキュリティ",
    categorySlug: "security",
    completed: true,
    watchedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
  },
];

const MOCK_COMMENTS: Comment[] = [
  {
    id: "cmt_001",
    videoId: "vid_001",
    userId: "user_001",
    displayName: "田中 太郎",
    text: "GitHubのセキュリティ設定についてとても分かりやすく説明されていました。特に2FAの設定手順が丁寧で助かりました！",
    likeCount: 12,
    likedByMe: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    replies: [
      {
        id: "cmt_001_r1",
        videoId: "vid_001",
        userId: "user_002",
        displayName: "鈴木 花子",
        text: "私も同じ感想です！アクセストークンの管理のところは今すぐ実践したいと思います。",
        likeCount: 3,
        likedByMe: false,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
        parentId: "cmt_001",
      },
    ],
  },
  {
    id: "cmt_002",
    videoId: "vid_001",
    userId: "user_003",
    displayName: "佐藤 次郎",
    text: "Social Engineering についても詳しく解説してほしいです。フィッシング対策がまだ不安なので。",
    likeCount: 7,
    likedByMe: true,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 10).toISOString(),
    replies: [],
  },
  {
    id: "cmt_003",
    videoId: "vid_001",
    userId: "user_004",
    displayName: "山田 三郎",
    text: "入社したばかりなので、このような動画があるととても勉強になります。他のセキュリティ動画も楽しみです。",
    likeCount: 5,
    likedByMe: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    replies: [],
  },
  {
    id: "cmt_004",
    videoId: "vid_002",
    userId: "user_002",
    displayName: "鈴木 花子",
    text: "コードレビューのチェックリスト、チームで共有します！PRテンプレートも作り直す良いきっかけになりました。",
    likeCount: 18,
    likedByMe: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    replies: [
      {
        id: "cmt_004_r1",
        videoId: "vid_002",
        userId: "user_001",
        displayName: "田中 太郎",
        text: "うちのチームでも活用しています。特にセルフレビューの観点が良かった！",
        likeCount: 4,
        likedByMe: false,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
        parentId: "cmt_004",
      },
      {
        id: "cmt_004_r2",
        videoId: "vid_002",
        userId: "user_005",
        displayName: "伊藤 四郎",
        text: "承認フローの部分が特に参考になりました。早速プロセス改善します。",
        likeCount: 2,
        likedByMe: false,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
        parentId: "cmt_004",
      },
    ],
  },
  {
    id: "cmt_005",
    videoId: "vid_005",
    userId: "user_003",
    displayName: "佐藤 次郎",
    text: "インシデント対応フローはすごく実践的でした。ポストモーテムの書き方まで解説してくれているのが嬉しい。",
    likeCount: 22,
    likedByMe: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
    replies: [],
  },
];

let _mockCommentStore: Comment[] = [...MOCK_COMMENTS];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function mockDelay(ms = 400) {
  await new Promise((res) => setTimeout(res, ms));
}

function getUserId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("user_id");
}

// ---------------------------------------------------------------------------
// Mock implementations
// ---------------------------------------------------------------------------

async function mockGetCategories(_params?: { locale?: string }): Promise<Category[]> {
  await mockDelay();
  return MOCK_CATEGORIES;
}

async function mockGetVideos(params?: {
  category?: string;
  search?: string;
  status?: string;
  limit?: number;
  offset?: number;
  locale?: string;
  publishedAfter?: string;
}): Promise<Video[]> {
  await mockDelay();
  let videos = MOCK_VIDEOS.filter((v) => !params?.status || v.status === params.status);
  if (params?.category) videos = videos.filter((v) => v.categorySlug === params.category);
  if (params?.search) {
    const s = params.search.toLowerCase();
    videos = videos.filter(
      (v) => v.title.toLowerCase().includes(s) || v.description?.toLowerCase().includes(s)
    );
  }
  if (params?.publishedAfter) {
    const after = new Date(params.publishedAfter).getTime();
    videos = videos.filter((v) => {
      const pub = v.publishedAt ? new Date(v.publishedAt).getTime() : new Date(v.createdAt).getTime();
      return pub >= after;
    });
  }
  const offset = params?.offset ?? 0;
  const limit = params?.limit ?? 50;
  return videos.slice(offset, offset + limit);
}

async function mockGetVideo(id: string): Promise<Video> {
  await mockDelay();
  const v = MOCK_VIDEOS.find((v) => v.id === id);
  if (!v) throw new Error(`動画が見つかりません: ${id}`);
  return v;
}

async function mockRecordWatch(videoId: string): Promise<void> {
  await mockDelay(200);
  const v = MOCK_VIDEOS.find((v) => v.id === videoId);
  if (v) v.watched = true;
}

async function mockGetWatchHistory(): Promise<WatchRecord[]> {
  await mockDelay();
  return MOCK_WATCH_HISTORY;
}

const _mockWatchLaterIds = new Set<string>();
const _mockLikedIds = new Set<string>();

async function mockToggleWatchLater(videoId: string): Promise<{ added: boolean }> {
  await mockDelay(150);
  if (_mockWatchLaterIds.has(videoId)) {
    _mockWatchLaterIds.delete(videoId);
    return { added: false };
  }
  _mockWatchLaterIds.add(videoId);
  return { added: true };
}

async function mockToggleLiked(videoId: string): Promise<{ added: boolean }> {
  await mockDelay(150);
  if (_mockLikedIds.has(videoId)) {
    _mockLikedIds.delete(videoId);
    return { added: false };
  }
  _mockLikedIds.add(videoId);
  return { added: true };
}

async function mockGetWatchLater(): Promise<Video[]> {
  await mockDelay();
  return MOCK_VIDEOS.filter((v) => _mockWatchLaterIds.has(v.id));
}

async function mockGetLikedVideos(): Promise<Video[]> {
  await mockDelay();
  return MOCK_VIDEOS.filter((v) => _mockLikedIds.has(v.id));
}

async function mockUserLogin(email: string, displayName: string): Promise<User> {
  await mockDelay(500);
  let user = MOCK_USERS.find((u) => u.email === email);
  if (!user) {
    user = { id: `user_${Date.now()}`, email, displayName, createdAt: new Date().toISOString() };
    MOCK_USERS.push(user);
  }
  _mockCurrentUser = user;
  if (typeof window !== "undefined") {
    localStorage.setItem("user_id", user.id);
    localStorage.setItem("user_email", user.email);
    localStorage.setItem("user_display_name", user.displayName);
  }
  return user;
}

async function mockGetCurrentUser(): Promise<User | null> {
  await mockDelay(200);
  if (_mockCurrentUser) return _mockCurrentUser;
  if (typeof window !== "undefined") {
    const id = localStorage.getItem("user_id");
    const email = localStorage.getItem("user_email");
    const displayName = localStorage.getItem("user_display_name");
    if (id && email && displayName) {
      _mockCurrentUser = { id, email, displayName, createdAt: new Date().toISOString() };
      return _mockCurrentUser;
    }
  }
  return null;
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

async function mockGetJobs(status?: string): Promise<Job[]> {
  await mockDelay();
  if (status && status !== "all") return MOCK_JOBS.filter((j) => j.status === status);
  return MOCK_JOBS;
}

async function mockGetJob(id: string): Promise<Job> {
  await mockDelay();
  const job = MOCK_JOBS.find((j) => j.id === id);
  if (!job) throw new Error(`ジョブが見つかりません: ${id}`);
  return job;
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
  return { base_url: "http://localhost:8000/api/v1", api_keys: ["local-te***key"], has_keys: true };
}

async function mockGetWikiSyncStatus(): Promise<WikiSyncStatus> {
  await mockDelay();
  return { last_sync_at: new Date().toISOString(), last_hash: "abc123def", total_articles: 3, is_syncing: false };
}

async function mockGetWikiDirectories(): Promise<WikiDirectory[]> {
  await mockDelay();
  return [
    {
      path: "",
      label: "ルート",
      count: 2,
      files: [
        { fileName: "README.md", path: "README.md" },
        { fileName: "CONTRIBUTING.md", path: "CONTRIBUTING.md" },
      ],
    },
    {
      path: "security",
      label: "security",
      count: 3,
      files: [
        { fileName: "github-security.md", path: "security/github-security.md" },
        { fileName: "incident-response.md", path: "security/incident-response.md" },
        { fileName: "zero-trust.md", path: "security/zero-trust.md" },
      ],
    },
    {
      path: "development",
      label: "development",
      count: 4,
      files: [
        { fileName: "code-review.md", path: "development/code-review.md" },
        { fileName: "tdd.md", path: "development/tdd.md" },
        { fileName: "branch-strategy.md", path: "development/branch-strategy.md" },
        { fileName: "coding-standards.md", path: "development/coding-standards.md" },
      ],
    },
  ];
}

async function mockTriggerWikiSyncFromDirectory(_payload: { path?: string; paths?: string[] }): Promise<WikiSyncResult> {
  await mockDelay(1000);
  return { status: "success", processed: 2, jobs_created: 2, hash: "abc123def" };
}

async function mockGetComments(videoId: string): Promise<Comment[]> {
  await mockDelay();
  return _mockCommentStore.filter((c) => c.videoId === videoId && !c.parentId);
}

async function mockCreateComment(videoId: string, req: CreateCommentRequest): Promise<Comment> {
  await mockDelay(300);
  const userId = getUserId() ?? "user_guest";
  const displayName =
    typeof window !== "undefined"
      ? (localStorage.getItem("user_display_name") ?? "ゲスト")
      : "ゲスト";

  const newComment: Comment = {
    id: `cmt_${Date.now()}`,
    videoId,
    userId,
    displayName,
    text: req.text,
    likeCount: 0,
    likedByMe: false,
    createdAt: new Date().toISOString(),
    parentId: req.parentId,
    replies: req.parentId ? undefined : [],
  };

  if (req.parentId) {
    const parent = _mockCommentStore.find((c) => c.id === req.parentId);
    if (parent) {
      parent.replies = [...(parent.replies ?? []), newComment];
    }
  } else {
    _mockCommentStore = [newComment, ..._mockCommentStore];
  }
  return newComment;
}

async function mockToggleCommentLike(commentId: string): Promise<Comment> {
  await mockDelay(200);
  const find = (list: Comment[]): Comment | undefined => {
    for (const c of list) {
      if (c.id === commentId) return c;
      if (c.replies) {
        const found = find(c.replies);
        if (found) return found;
      }
    }
    return undefined;
  };
  const comment = find(_mockCommentStore);
  if (!comment) throw new Error("コメントが見つかりません");
  comment.likedByMe = !comment.likedByMe;
  comment.likeCount += comment.likedByMe ? 1 : -1;
  return comment;
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

async function mockGetAdminArticles(): Promise<ArticleRecord[]> {
  await mockDelay();
  return [
    { id: "art_001", title: "GitHubセキュリティ運用ガイドライン", gitPath: "security/github-security.md", gitHash: "abc123", categoryId: "cat_001", categoryName: "セキュリティ", latestVideoId: "vid_001", latestVideoStatus: "ready", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: "art_002", title: "コードレビュー規約", gitPath: "development/code-review.md", gitHash: "def456", categoryId: "cat_002", categoryName: "開発規約", latestVideoId: "vid_002", latestVideoStatus: "ready", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: "art_003", title: "AWSリソース命名規則", gitPath: "infrastructure/aws-naming.md", gitHash: "ghi789", categoryId: "cat_003", categoryName: "インフラ", latestVideoId: "vid_003", latestVideoStatus: "generating", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  ];
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
  if (!userId) return;
  await fetch(`${BASE_URL}/videos/${videoId}/watch`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-user-id": userId },
    body: JSON.stringify({ completed }),
  });
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
    return res.json();
  } catch {
    return null;
  }
}

async function realGetStats(): Promise<JobStats> {
  const res = await fetch(`${BASE_URL}/jobs/stats`);
  if (!res.ok) throw new Error("統計情報の取得に失敗しました");
  return res.json();
}

async function realGetJobs(status?: string): Promise<Job[]> {
  const p = new URLSearchParams();
  if (status && status !== "all") p.set("status", status);
  const url = p.toString() ? `${BASE_URL}/jobs?${p}` : `${BASE_URL}/jobs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("ジョブ一覧の取得に失敗しました");
  return res.json();
}

async function realGetJob(id: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/jobs/${id}`);
  if (!res.ok) throw new Error(`ジョブの取得に失敗しました: ${id}`);
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

async function realGetApiInfo(): Promise<ApiInfo> {
  const res = await fetch(`${BASE_URL}/settings/api-info`);
  if (!res.ok) throw new Error("API情報の取得に失敗しました");
  return res.json();
}

async function realGetWikiSyncStatus(): Promise<WikiSyncStatus> {
  const res = await fetch(`${BASE_URL}/wiki/sync-status`);
  if (!res.ok) throw new Error("Wiki同期状態の取得に失敗しました");
  return res.json();
}

async function realGetAdminArticles(): Promise<ArticleRecord[]> {
  const res = await fetch(`${BASE_URL}/admin/articles`);
  if (!res.ok) throw new Error("記事一覧の取得に失敗しました");
  return res.json();
}

async function realGetWikiDirectories(): Promise<WikiDirectory[]> {
  const res = await fetch(`${BASE_URL}/wiki/directories`);
  if (!res.ok) throw new Error("ディレクトリ一覧の取得に失敗しました");
  return res.json();
}

async function realTriggerWikiSyncFromDirectory(payload: { path?: string; paths?: string[] }): Promise<WikiSyncResult> {
  const res = await fetch(`${BASE_URL}/wiki/sync-directory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("ディレクトリの動画作成の開始に失敗しました");
  return res.json();
}

// ---------------------------------------------------------------------------
// Exported API client
// ---------------------------------------------------------------------------

export const api = {
  // E-learning
  getCategories: USE_MOCK ? mockGetCategories : realGetCategories,
  getVideos: USE_MOCK ? mockGetVideos : realGetVideos,
  getVideo: USE_MOCK ? mockGetVideo : realGetVideo,
  recordWatch: USE_MOCK ? mockRecordWatch : realRecordWatch,
  getWatchHistory: USE_MOCK ? mockGetWatchHistory : realGetWatchHistory,
  toggleWatchLater: USE_MOCK ? mockToggleWatchLater : realToggleWatchLater,
  toggleLiked: USE_MOCK ? mockToggleLiked : realToggleLiked,
  getWatchLater: USE_MOCK ? mockGetWatchLater : realGetWatchLater,
  getLikedVideos: USE_MOCK ? mockGetLikedVideos : realGetLikedVideos,
  userLogin: USE_MOCK ? mockUserLogin : realUserLogin,
  getCurrentUser: USE_MOCK ? mockGetCurrentUser : realGetCurrentUser,

  // Wiki (admin)
  getWikiSyncStatus: USE_MOCK ? mockGetWikiSyncStatus : realGetWikiSyncStatus,
  getWikiDirectories: USE_MOCK ? mockGetWikiDirectories : realGetWikiDirectories,
  triggerWikiSyncFromDirectory: USE_MOCK ? mockTriggerWikiSyncFromDirectory : realTriggerWikiSyncFromDirectory,
  getAdminArticles: USE_MOCK ? mockGetAdminArticles : realGetAdminArticles,

  // Jobs (admin)
  getStats: USE_MOCK ? mockGetStats : realGetStats,
  getJobs: USE_MOCK ? mockGetJobs : realGetJobs,
  getJob: USE_MOCK ? mockGetJob : realGetJob,

  // NotebookLM Auth (admin)
  getAuthStatus: USE_MOCK ? mockGetAuthStatus : realGetAuthStatus,
  triggerLogin: USE_MOCK ? mockTriggerLogin : realTriggerLogin,
  getApiInfo: USE_MOCK ? mockGetApiInfo : realGetApiInfo,

  // Comments
  getComments: USE_MOCK
    ? (videoId: string) => mockGetComments(videoId)
    : (videoId: string) => realGetComments(videoId),
  createComment: USE_MOCK
    ? (videoId: string, req: CreateCommentRequest) => mockCreateComment(videoId, req)
    : (videoId: string, req: CreateCommentRequest) => realCreateComment(videoId, req),
  toggleCommentLike: USE_MOCK
    ? (commentId: string) => mockToggleCommentLike(commentId)
    : (commentId: string) => realToggleCommentLike(commentId),

  getVideoStreamUrl(id: string, jobId: string): string {
    if (USE_MOCK) return "";
    return `${BASE_URL}/videos/${id}/stream`;
  },

  getDownloadUrl(jobId: string): string {
    return `${BASE_URL}/jobs/${jobId}/download`;
  },
};
