"use client";

import type { VideoFormat } from "@/lib/types";
import { cn } from "@/lib/utils";

interface FormatSelectorProps {
  value: VideoFormat;
  onChange: (format: VideoFormat) => void;
}

const FORMATS: { value: VideoFormat; label: string; description: string }[] = [
  {
    value: "explainer",
    label: "解説型",
    description: "詳細な解説・分析向け（5〜10分程度）",
  },
  {
    value: "brief",
    label: "短縮版",
    description: "要点を簡潔に（1〜3分程度）",
  },
];

export function FormatSelector({ value, onChange }: FormatSelectorProps) {
  return (
    <div className="grid grid-cols-2 gap-2.5">
      {FORMATS.map((fmt) => {
        const isSelected = value === fmt.value;
        return (
          <button
            key={fmt.value}
            type="button"
            onClick={() => onChange(fmt.value)}
            className={cn(
              "flex flex-col gap-1 p-3.5 rounded-lg border text-left transition-all duration-150",
              isSelected
                ? "border-primary bg-accent ring-1 ring-primary/20"
                : "border-border bg-background hover:bg-muted/40"
            )}
          >
            <span className={cn("text-sm font-medium", isSelected ? "text-primary" : "text-foreground")}>
              {fmt.label}
            </span>
            <span className="text-xs text-muted-foreground">{fmt.description}</span>
          </button>
        );
      })}
    </div>
  );
}
