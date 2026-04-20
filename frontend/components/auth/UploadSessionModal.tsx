"use client";

import { useState } from "react";
import { X, UploadCloud, Save, Loader2, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

type Status = "idle" | "saving" | "auth_saved" | "error";

interface UploadSessionModalProps {
  open: boolean;
  onClose: () => void;
  onAuthSaved?: () => void;
}

export default function UploadSessionModal({ open, onClose, onAuthSaved }: UploadSessionModalProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [jsonText, setJsonText] = useState("");
  const [showInstructions, setShowInstructions] = useState(true);

  if (!open) return null;

  const handleSave = async () => {
    if (!jsonText.trim()) {
      setStatus("error");
      setStatusMsg("JSONデータを入力してください。");
      return;
    }

    try {
      setStatus("saving");
      setStatusMsg("認証情報を保存中...");
      
      const res = await api.uploadNotebookLMSession(jsonText.trim());
      
      setStatus("auth_saved");
      setStatusMsg(res.message || "認証情報を保存しました。");
      onAuthSaved?.();
    } catch (e: any) {
      setStatus("error");
      setStatusMsg(e.message || "保存に失敗しました。JSONの形式を確認してください。");
    }
  };

  const handleCancel = () => {
    setStatus("idle");
    setJsonText("");
    setStatusMsg("");
    onClose();
  };

  const isDone = status === "auth_saved";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative flex flex-col bg-background rounded-2xl shadow-2xl border border-border w-[95vw] max-w-[700px] max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-muted/30">
          <div className="flex items-center gap-2">
            <UploadCloud className="size-4 text-primary" />
            <span className="text-sm font-semibold text-foreground">Save NotebookLM Credential</span>
          </div>
          <button
            onClick={handleCancel}
            className="size-8 rounded-lg flex items-center justify-center hover:bg-muted transition-colors"
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-5 space-y-4 bg-white">
          <div className="rounded-lg border border-border overflow-hidden">
            <button 
              className="flex items-center justify-between w-full px-4 py-2.5 bg-muted/40 hover:bg-muted/60 transition-colors text-sm font-medium text-left"
              onClick={() => setShowInstructions(!showInstructions)}
            >
              <div className="flex items-center gap-2">
                <Info className="size-4 text-primary" />
                エクスポート手順 (Cookie-Editor)
              </div>
              <span className="text-xs text-muted-foreground">{showInstructions ? "隠す" : "表示"}</span>
            </button>
            
            {showInstructions && (
              <div className="px-4 py-3 text-sm text-muted-foreground space-y-2 border-t border-border bg-muted/10">
                <ol className="list-decimal list-inside space-y-1.5 marker:text-muted-foreground">
                  <li>Chrome拡張機能 <strong>Cookie-Editor</strong> をインストールします。</li>
                  <li>
                    ブラウザで <a href="https://notebooklm.google.com/" target="_blank" rel="noreferrer" className="text-primary hover:underline">NotebookLM</a> にアクセスし、Googleアカウントでログインします。
                  </li>
                  <li>ログイン完了後、画面右上の Cookie-Editor 拡張機能アイコンをクリックします。</li>
                  <li>メニューから <strong>Export</strong> (エクスポート) アイコンをクリックします。(JSONデータがクリップボードにコピーされます)</li>
                  <li>下の入力欄にコピーしたJSONデータを貼り付けて「保存」を押してください。</li>
                </ol>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-foreground">
              JSONデータ
            </label>
            <textarea
              className="w-full h-40 p-3 rounded-lg border border-input bg-transparent text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring font-mono"
              placeholder='[ { "domain": ".google.com", "name": "__Secure-1PSID", ... } ]'
              value={jsonText}
              onChange={(e) => {
                setJsonText(e.target.value);
                if (status === "error") setStatus("idle");
              }}
              disabled={status === "saving" || status === "auth_saved"}
            />
          </div>

          {statusMsg && (
            <div className={`text-sm p-3 rounded-lg ${
              status === "error" ? "bg-red-50 text-red-700 border border-red-200" :
              status === "auth_saved" ? "bg-green-50 text-green-700 border border-green-200" :
              "bg-blue-50 text-blue-700 border border-blue-200"
            }`}>
              {statusMsg}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-border bg-muted/30">
          <p className="text-xs text-muted-foreground">
            エクスポートしたJSONを安全に保存し、バックグラウンドでのAI動画生成に使用します。
          </p>
          <div className="flex items-center gap-2 pl-4">
            <Button
              size="sm"
              variant="outline"
              onClick={handleCancel}
              disabled={status === "saving"}
            >
              {isDone ? "閉じる" : "キャンセル"}
            </Button>
            {!isDone && (
              <Button
                size="sm"
                onClick={handleSave}
                disabled={status === "saving" || !jsonText.trim()}
                className="gap-1.5"
              >
                {status === "saving" ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Save className="size-3.5" />
                )}
                {status === "saving" ? "保存中..." : "保存"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
