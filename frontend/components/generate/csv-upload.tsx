"use client";

import { useCallback, useRef } from "react";
import { Upload, FileSpreadsheet, X, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface CsvUploadProps {
  value: File[];
  onChange: (files: File[]) => void;
  error?: string;
}

export function CsvUpload({ value, onChange, error }: CsvUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      const newFiles = Array.from(incoming).filter((f) =>
        f.name.toLowerCase().endsWith(".csv")
      );
      if (newFiles.length === 0) return;

      // 重複（同名）を除去して追加
      const existing = new Set(value.map((f) => f.name));
      const deduped = newFiles.filter((f) => !existing.has(f.name));
      onChange([...value, ...deduped]);
    },
    [value, onChange]
  );

  const removeFile = useCallback(
    (name: string) => {
      onChange(value.filter((f) => f.name !== name));
    },
    [value, onChange]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) addFiles(e.target.files);
      e.target.value = "";
    },
    [addFiles]
  );

  return (
    <div className="space-y-2">
      {/* File list */}
      {value.length > 0 && (
        <ul className="space-y-1.5">
          {value.map((file) => (
            <li
              key={file.name}
              className="flex items-center gap-3 px-4 py-2.5 border border-border rounded-lg bg-muted/30"
            >
              <div className="flex items-center justify-center size-8 rounded-md bg-green-50 shrink-0">
                <FileSpreadsheet className="size-4 text-green-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate text-foreground">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeFile(file.name)}
                className="size-7 p-0 text-muted-foreground hover:text-destructive shrink-0"
                aria-label={`${file.name} を削除`}
              >
                <X className="size-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      {/* Drop zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex flex-col items-center justify-center gap-3 px-6 py-8 border-2 border-dashed rounded-lg cursor-pointer transition-colors",
          error && value.length === 0
            ? "border-destructive/50 bg-destructive/5 hover:bg-destructive/10"
            : "border-border bg-muted/20 hover:bg-muted/40 hover:border-border"
        )}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        aria-label="CSVファイルを追加"
      >
        <div className="flex items-center justify-center size-9 rounded-full bg-muted">
          {value.length > 0 ? (
            <Plus className="size-4 text-muted-foreground" />
          ) : (
            <Upload className="size-4 text-muted-foreground" />
          )}
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">
            {value.length > 0
              ? "さらにファイルを追加"
              : "ファイルをドロップ、またはクリックして選択"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            CSVファイル (.csv) · 複数選択可
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          multiple
          className="sr-only"
          onChange={handleInputChange}
          aria-label="CSVファイルを選択"
        />
      </div>

      {error && value.length === 0 && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
}
