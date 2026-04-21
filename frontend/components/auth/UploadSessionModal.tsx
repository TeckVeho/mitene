"use client";

import { useRef, useState } from "react";
import { UploadCloud, Save, Loader2, Info, Copy, FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

type Status = "idle" | "saving" | "auth_saved" | "error";

/** Bookmark URL field: paste this entire line. Only non-httpOnly cookies are visible to JS — use Cookie-Editor for a full session. */
const NOTEBOOKLM_STATE_BOOKMARKLET = `javascript:(function(){
  const state = {
    cookies: document.cookie.split('; ').filter(Boolean).map(function(c) {
      var eq = c.indexOf('=');
      var name = eq === -1 ? c : c.slice(0, eq);
      var value = eq === -1 ? '' : c.slice(eq + 1);
      return {
        name: name,
        value: value,
        domain: window.location.hostname,
        path: '/',
        expires: Date.now() / 1000 + 86400,
        secure: true,
        sameSite: 'Lax'
      };
    }),
    origins: [{
      origin: window.location.origin,
      localStorage: Object.keys(localStorage).map(function(k) {
        return { name: k, value: localStorage.getItem(k) || '' };
      })
    }]
  };
  var blob = new Blob([JSON.stringify(state)], {type: 'application/json'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'notebooklm_state.json';
  a.click();
})();`;

/** Same bookmarklet without the `javascript:` prefix (for managers that have a separate "Script" field). */
const NOTEBOOKLM_STATE_BOOKMARKLET_SCRIPT = NOTEBOOKLM_STATE_BOOKMARKLET.replace(/^javascript:/i, "");

interface UploadSessionModalProps {
  /** 認証保存後に親（例: 管理画面）でステータス再取得する */
  onAuthSaved?: () => void;
}

export default function UploadSessionModal({ onAuthSaved }: UploadSessionModalProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [jsonText, setJsonText] = useState("");
  const [showCookieEditorHelp, setShowCookieEditorHelp] = useState(true);
  const [showBookmarkHelp, setShowBookmarkHelp] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const copyText = async (text: string, okMessage: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setStatus("idle");
      setStatusMsg(okMessage);
      setTimeout(() => {
        setStatusMsg((m) => (m === okMessage ? "" : m));
      }, 2000);
    } catch {
      setStatus("error");
      setStatusMsg("クリップボードへのコピーに失敗しました。");
    }
  };

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
    } catch (e: unknown) {
      setStatus("error");
      setStatusMsg(e instanceof Error ? e.message : "保存に失敗しました。JSONの形式を確認してください。");
    }
  };

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    try {
      setStatus("saving");
      setStatusMsg("認証情報を保存中...");

      const res = await api.uploadNotebookLMSessionFile(file);

      setStatus("auth_saved");
      setStatusMsg(res.message || "認証情報を保存しました。");
      onAuthSaved?.();
    } catch (err: unknown) {
      setStatus("error");
      setStatusMsg(err instanceof Error ? err.message : "ファイルのアップロードに失敗しました。");
    }
  };

  const handleClearForm = () => {
    setStatus("idle");
    setJsonText("");
    setStatusMsg("");
  };

  const isDone = status === "auth_saved";

  return (
    <div className="rounded-xl border border-border bg-background shadow-sm overflow-hidden max-h-[min(80vh,720px)] flex flex-col">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border bg-muted/30 shrink-0">
        <UploadCloud className="size-4 text-primary shrink-0" />
        <span className="text-sm font-semibold text-foreground">Save NotebookLM Credential</span>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
          <div className="rounded-lg border border-border overflow-hidden">
            <button
              type="button"
              className="flex items-center justify-between w-full px-4 py-2.5 bg-muted/40 hover:bg-muted/60 transition-colors text-sm font-medium text-left"
              onClick={() => setShowBookmarkHelp(!showBookmarkHelp)}
            >
              <div className="flex items-center gap-2">
                <Info className="size-4 text-primary" />
                ブックマークレット（JSON ファイルをダウンロード）
              </div>
              <span className="text-xs text-muted-foreground">{showBookmarkHelp ? "隠す" : "表示"}</span>
            </button>

            {showBookmarkHelp && (
              <div className="px-4 py-3 text-sm text-muted-foreground space-y-3 border-t border-border bg-muted/10">
                <p className="text-amber-800 bg-amber-50 border border-amber-200 rounded-md p-2 text-xs leading-relaxed">
                  <strong>注意:</strong> ブラウザの <code className="font-mono">document.cookie</code>{" "}
                  では <strong>httpOnly</strong> の Cookie（多くの Google セッションに必要な{" "}
                  <code className="font-mono">SID</code> など）が読めません。ブックマークレットだけでは認証が通らない場合は、下の{" "}
                  <strong>Cookie-Editor</strong> または <strong>notebooklm login</strong> を利用してください。
                </p>
                <p>新しいブックマークを作成し、次のとおりに設定します。</p>
                <dl className="space-y-2 text-foreground">
                  <div>
                    <dt className="font-semibold text-xs text-muted-foreground uppercase tracking-wide">名前 / Name</dt>
                    <dd className="mt-0.5 font-mono text-xs bg-muted/50 rounded px-2 py-1 break-all">NotebookLM state export</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-xs text-muted-foreground uppercase tracking-wide">URL</dt>
                    <dd className="mt-1 flex flex-col gap-2">
                      <textarea
                        readOnly
                        className="w-full min-h-[88px] p-2 rounded-md border border-input bg-white text-[11px] leading-snug font-mono break-all"
                        value={NOTEBOOKLM_STATE_BOOKMARKLET}
                        aria-label="Bookmarklet URL"
                      />
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="self-start gap-1"
                        onClick={() => copyText(NOTEBOOKLM_STATE_BOOKMARKLET, "URL をコピーしました")}
                      >
                        <Copy className="size-3.5" />
                        URL をコピー
                      </Button>
                    </dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-xs text-muted-foreground uppercase tracking-wide">
                      スクリプト（<code className="font-mono normal-case">javascript:</code> を除く）
                    </dt>
                    <dd className="mt-1 flex flex-col gap-2">
                      <textarea
                        readOnly
                        className="w-full min-h-[120px] p-2 rounded-md border border-input bg-white text-[11px] leading-snug font-mono break-all"
                        value={NOTEBOOKLM_STATE_BOOKMARKLET_SCRIPT}
                        aria-label="Bookmarklet script without javascript prefix"
                      />
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="self-start gap-1"
                        onClick={() => copyText(NOTEBOOKLM_STATE_BOOKMARKLET_SCRIPT, "スクリプトをコピーしました")}
                      >
                        <Copy className="size-3.5" />
                        スクリプトをコピー
                      </Button>
                    </dd>
                  </div>
                </dl>
                <ol className="list-decimal list-inside space-y-1.5 marker:text-muted-foreground">
                  <li>
                    <a href="https://notebooklm.google.com/" target="_blank" rel="noreferrer" className="text-primary hover:underline">
                      NotebookLM
                    </a>
                    にログインした状態で、作成したブックマークをクリックします。
                  </li>
                  <li>
                    <code className="font-mono text-xs">notebooklm_state.json</code> がダウンロードされたら、下の「state
                    ファイルをアップロード」からそのファイルを選びます。
                  </li>
                </ol>
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border p-4 space-y-2 bg-muted/10">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="text-sm font-semibold text-foreground">state ファイルをアップロード</label>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={handleFileSelected}
                disabled={status === "saving" || status === "auth_saved"}
              />
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="gap-1.5"
                disabled={status === "saving" || status === "auth_saved"}
                onClick={() => fileInputRef.current?.click()}
              >
                {status === "saving" ? <Loader2 className="size-3.5 animate-spin" /> : <FileUp className="size-3.5" />}
                JSON を選択
              </Button>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Playwright の <code className="font-mono">storage_state</code> 形式（
              <code className="font-mono">cookies</code> / <code className="font-mono">origins</code>
              ）または Cookie-Editor の配列 JSON を 1 ファイルにまとめたものをアップロードできます。サーバーに保存され、設定に応じて GCS にも同期されます。
            </p>
          </div>

          <div className="rounded-lg border border-border overflow-hidden">
            <button
              type="button"
              className="flex items-center justify-between w-full px-4 py-2.5 bg-muted/40 hover:bg-muted/60 transition-colors text-sm font-medium text-left"
              onClick={() => setShowCookieEditorHelp(!showCookieEditorHelp)}
            >
              <div className="flex items-center gap-2">
                <Info className="size-4 text-primary" />
                エクスポート手順 (Cookie-Editor)
              </div>
              <span className="text-xs text-muted-foreground">{showCookieEditorHelp ? "隠す" : "表示"}</span>
            </button>

            {showCookieEditorHelp && (
              <div className="px-4 py-3 text-sm text-muted-foreground space-y-2 border-t border-border bg-muted/10">
                <ol className="list-decimal list-inside space-y-1.5 marker:text-muted-foreground">
                  <li>
                    Chrome拡張機能 <strong>Cookie-Editor</strong> をインストールします。
                  </li>
                  <li>
                    ブラウザで{" "}
                    <a href="https://notebooklm.google.com/" target="_blank" rel="noreferrer" className="text-primary hover:underline">
                      NotebookLM
                    </a>{" "}
                    にアクセスし、Googleアカウントでログインします。
                  </li>
                  <li>ログイン完了後、画面右上の Cookie-Editor 拡張機能アイコンをクリックします。</li>
                  <li>
                    メニューから <strong>Export</strong> → <strong>JSON</strong> でエクスポートします。
                  </li>
                  <li>下の入力欄に貼り付けるか、上のファイルアップロードに同じ JSON を保存して選択してください。</li>
                </ol>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-foreground">JSONデータ（貼り付け）</label>
            <textarea
              className="w-full h-40 p-3 rounded-lg border border-input bg-transparent text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring font-mono"
              placeholder='Cookie-Editor: [ { "domain": ".google.com", "name": "SID", ... } ] または {"cookies":[...],"origins":[...]}'
              value={jsonText}
              onChange={(e) => {
                setJsonText(e.target.value);
                if (status === "error") setStatus("idle");
              }}
              disabled={status === "saving" || status === "auth_saved"}
            />
          </div>

          {statusMsg && (
            <div
              className={`text-sm p-3 rounded-lg whitespace-pre-wrap ${
                status === "error"
                  ? "bg-red-50 text-red-700 border border-red-200"
                  : status === "auth_saved"
                    ? "bg-green-50 text-green-700 border border-green-200"
                    : "bg-blue-50 text-blue-700 border border-blue-200"
              }`}
            >
              {statusMsg}
            </div>
          )}
        </div>

      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-t border-border bg-muted/20 shrink-0">
        <p className="text-xs text-muted-foreground flex-1 min-w-48">
          エクスポートした JSON はサーバーに保存され、設定に応じて GCS にも同期されます。Remote Login とは別の方法です。
        </p>
        <div className="flex items-center gap-2 shrink-0">
          {(jsonText.trim() || isDone) && status !== "saving" && (
            <Button type="button" size="sm" variant="outline" onClick={handleClearForm}>
              {isDone ? "続けて入力" : "クリア"}
            </Button>
          )}
          {!isDone && (
            <Button
              type="button"
              size="sm"
              onClick={handleSave}
              disabled={status === "saving" || !jsonText.trim()}
              className="gap-1.5"
            >
              {status === "saving" ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />}
              {status === "saving" ? "保存中..." : "保存"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
