"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Copy, Key, Link2, Terminal, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

// ---------------------------------------------------------------------------
// Endpoint definitions
// ---------------------------------------------------------------------------

const ENDPOINTS = [
  {
    method: "POST",
    path: "/jobs",
    summary: "動画生成ジョブ作成",
    description: "CSVファイルをBase64またはサーバーパスで指定し、動画生成ジョブを作成します。ジョブIDを即時返却し、バックグラウンドで処理を開始します。",
  },
  {
    method: "GET",
    path: "/jobs",
    summary: "ジョブ一覧取得",
    description: "全ジョブの一覧を返します。?status=processing などでフィルタリングできます。",
  },
  {
    method: "GET",
    path: "/jobs/{id}",
    summary: "ジョブ状態取得",
    description: "指定ジョブの現在の状態を返します。status フィールドは pending / processing / completed / error のいずれかです。",
  },
  {
    method: "GET",
    path: "/jobs/{id}/download",
    summary: "動画ダウンロード",
    description: "完了したジョブのMP4動画をダウンロードします。S3有効時は署名付きURLへリダイレクトします。",
  },
  {
    method: "POST",
    path: "/audio-jobs",
    summary: "音声ジョブ作成",
    description: "CSVからGemini TTSを使って音声解説（WAV）を生成するジョブを作成します。",
  },
  {
    method: "GET",
    path: "/audio-jobs/{id}",
    summary: "音声ジョブ状態取得",
    description: "指定した音声ジョブの現在の状態を返します。completed になると generatedScript フィールドに解説原稿が含まれます。",
  },
  {
    method: "GET",
    path: "/audio-jobs/{id}/download",
    summary: "音声ダウンロード",
    description: "完了した音声ジョブのWAVファイルをダウンロードします。",
  },
] as const;

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MethodBadge({ method }: { method: "GET" | "POST" }) {
  return (
    <Badge
      variant={method === "POST" ? "default" : "secondary"}
      className="font-mono text-[11px] shrink-0"
    >
      {method}
    </Badge>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button variant="ghost" size="icon" className="size-7 shrink-0" onClick={handleCopy}>
      {copied ? <Check className="size-3.5 text-green-500" /> : <Copy className="size-3.5" />}
    </Button>
  );
}

function CodeBlock({ children }: { children: string }) {
  return (
    <div className="relative group">
      <pre className="rounded-md bg-muted px-4 py-3 text-xs font-mono overflow-x-auto leading-relaxed text-muted-foreground whitespace-pre">
        {children}
      </pre>
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <CopyButton text={children} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ApiInfoPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["api-info"],
    queryFn: () => api.getApiInfo(),
  });

  const baseUrl = data?.base_url ?? "http://localhost:8000/api/v1";
  const apiKey = data?.api_keys?.[0] ?? "(未設定)";
  const hasKeys = data?.has_keys ?? false;

  const curlVideoExample = `curl -X POST "${baseUrl}/jobs" \\
  -H "X-API-Key: <YOUR_API_KEY>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "notebook_title": "月次レポート",
    "instructions": "CSVデータの主要な傾向を解説してください",
    "style": "whiteboard",
    "format": "explainer",
    "language": "ja",
    "csv_files": [
      {
        "filename": "report.csv",
        "content_base64": "<BASE64_ENCODED_CSV>"
      }
    ]
  }'`;

  const curlStatusExample = `curl "${baseUrl}/jobs/{job_id}" \\
  -H "X-API-Key: <YOUR_API_KEY>"`;

  const curlAudioExample = `curl -X POST "${baseUrl}/audio-jobs" \\
  -H "X-API-Key: <YOUR_API_KEY>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "CSV音声解説",
    "instructions": "データの傾向を音声で解説してください",
    "voice_name": "Kore",
    "language": "ja",
    "csv_files": [
      {
        "filename": "data.csv",
        "content_base64": "<BASE64_ENCODED_CSV>"
      }
    ]
  }'`;

  return (
    <div className="space-y-6">
      {/* API接続情報 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="size-4" />
            接続情報
          </CardTitle>
          <CardDescription>外部システムからAPIを呼び出す際に使用する接続情報です。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3">
            <div className="flex items-center justify-between rounded-lg border px-4 py-3">
              <div className="space-y-0.5">
                <p className="text-xs text-muted-foreground font-medium">ベースURL</p>
                {isLoading ? (
                  <div className="h-4 w-64 animate-pulse rounded bg-muted" />
                ) : (
                  <p className="font-mono text-sm">{baseUrl}</p>
                )}
              </div>
              <CopyButton text={baseUrl} />
            </div>

            <div className="flex items-center justify-between rounded-lg border px-4 py-3">
              <div className="space-y-0.5">
                <p className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                  <Key className="size-3" />
                  APIキー
                  {!hasKeys && !isLoading && (
                    <Badge variant="outline" className="text-[10px] ml-1">未設定</Badge>
                  )}
                </p>
                {isLoading ? (
                  <div className="h-4 w-40 animate-pulse rounded bg-muted" />
                ) : isError ? (
                  <p className="font-mono text-sm text-destructive">取得エラー</p>
                ) : (
                  <p className="font-mono text-sm">{apiKey}</p>
                )}
              </div>
              {!isLoading && !isError && hasKeys && <CopyButton text={data?.api_keys?.[0] ?? ""} />}
            </div>
          </div>

          {!hasKeys && !isLoading && (
            <p className="text-xs text-muted-foreground rounded-md bg-muted/50 px-3 py-2">
              APIキーを設定するには、バックエンドの環境変数 <code className="font-mono">NOTEVIDEO_API_KEYS</code> にカンマ区切りでキーを設定してください。
            </p>
          )}
        </CardContent>
      </Card>

      {/* 認証方法 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Key className="size-4" />
            認証方法
          </CardTitle>
          <CardDescription>全ての外部APIエンドポイントで <code className="font-mono text-xs">X-API-Key</code> ヘッダーが必要です。</CardDescription>
        </CardHeader>
        <CardContent>
          <CodeBlock>{`X-API-Key: <YOUR_API_KEY>`}</CodeBlock>
          <p className="mt-3 text-xs text-muted-foreground">
            環境変数 <code className="font-mono">NOTEVIDEO_API_KEYS</code> が未設定の場合、開発環境として認証がスキップされます。
          </p>
        </CardContent>
      </Card>

      {/* エンドポイント一覧 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Zap className="size-4" />
            エンドポイント一覧
          </CardTitle>
          <CardDescription>ベースURL以降のパスです。全リクエストに <code className="font-mono text-xs">X-API-Key</code> ヘッダーが必要です。</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {ENDPOINTS.map((ep, i) => (
              <div key={i} className="flex items-start gap-3 px-6 py-3.5">
                <MethodBadge method={ep.method} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <code className="text-sm font-mono text-foreground">{ep.path}</code>
                    <span className="text-xs text-muted-foreground">— {ep.summary}</span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">{ep.description}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* cURLサンプル */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Terminal className="size-4" />
            cURL サンプル
          </CardTitle>
          <CardDescription>コピーしてすぐに試せるリクエスト例です。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">動画生成ジョブ作成</p>
            <CodeBlock>{curlVideoExample}</CodeBlock>
          </div>
          <Separator />
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">ジョブ状態確認</p>
            <CodeBlock>{curlStatusExample}</CodeBlock>
          </div>
          <Separator />
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">音声ジョブ作成</p>
            <CodeBlock>{curlAudioExample}</CodeBlock>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
