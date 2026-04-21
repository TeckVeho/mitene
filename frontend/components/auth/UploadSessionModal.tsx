"use client";

import { useEffect, useRef, useState } from "react";
import { X, UploadCloud, Loader2, FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/locale-context";

type Status = "idle" | "saving" | "error";

const CHROME_WEBSTORE_SEARCH =
  "https://chromewebstore.google.com/search/Cookie%20%26%20Storage%20Exporter";

interface UploadSessionModalProps {
  open: boolean;
  onClose: () => void;
  onAuthSaved?: () => void;
}

export default function UploadSessionModal({ open, onClose, onAuthSaved }: UploadSessionModalProps) {
  const { t } = useLocale();
  const [status, setStatus] = useState<Status>("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setStatus("idle");
      setStatusMsg("");
    }
  }, [open]);

  if (!open) return null;

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    try {
      setStatus("saving");
      setStatusMsg("");

      await api.uploadNotebookLMSessionFile(file);

      setStatus("idle");
      onAuthSaved?.();
      onClose();
    } catch (err: unknown) {
      setStatus("error");
      setStatusMsg(err instanceof Error ? err.message : "ファイルのアップロードに失敗しました。");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="relative flex w-full max-w-lg flex-col rounded-2xl border border-neutral-200 bg-white text-neutral-900 shadow-2xl dark:border-neutral-200 dark:bg-neutral-50 dark:text-neutral-900">
        <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-100/90 px-4 py-3 dark:bg-neutral-100">
          <div className="flex items-center gap-2">
            <UploadCloud className="size-4 shrink-0 text-primary" />
            <span className="text-sm font-semibold text-neutral-900">{t.admin.notebookLMCookieModalTitle}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-lg text-neutral-600 hover:bg-neutral-200/90 disabled:opacity-50"
            aria-label="Close"
            disabled={status === "saving"}
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="space-y-4 p-4">
          <ol className="list-decimal space-y-2 pl-4 text-sm text-neutral-600 marker:text-neutral-500">
            <li>
              {t.admin.notebookLMCookieModalStep1}{" "}
              <a
                href={CHROME_WEBSTORE_SEARCH}
                target="_blank"
                rel="noreferrer"
                className="text-primary underline hover:no-underline"
              >
                Chrome Web Store
              </a>
            </li>
            <li>
              <a
                href="https://notebooklm.google.com/"
                target="_blank"
                rel="noreferrer"
                className="text-primary underline hover:no-underline"
              >
                https://notebooklm.google.com/
              </a>
              {t.admin.notebookLMCookieModalStep2}
            </li>
            <li>{t.admin.notebookLMCookieModalStep3}</li>
          </ol>

          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={handleFileSelected}
            disabled={status === "saving"}
          />
          <Button
            type="button"
            className="w-full gap-2 sm:w-auto"
            disabled={status === "saving"}
            onClick={() => fileInputRef.current?.click()}
          >
            {status === "saving" ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <FileUp className="size-4" />
            )}
            {status === "saving" ? t.admin.notebookLMCookieUploading : t.admin.notebookLMCookieUploadButton}
          </Button>

          {status === "error" && statusMsg && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm whitespace-pre-wrap text-red-700">
              {statusMsg}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
