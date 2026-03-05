"use client";

import { VIDEO_STYLE_LABELS } from "@/lib/types";
import type { VideoStyle } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface StyleSelectorProps {
  value: VideoStyle;
  onChange: (style: VideoStyle) => void;
}

const STYLE_ICONS: Record<VideoStyle, string> = {
  auto: "✨",
  classic: "🎬",
  whiteboard: "📋",
  kawaii: "🌸",
  anime: "⚡",
  watercolor: "🎨",
  "retro-print": "📰",
  heritage: "🏛️",
  "paper-craft": "📦",
};

export function StyleSelector({ value, onChange }: StyleSelectorProps) {
  const styles = Object.entries(VIDEO_STYLE_LABELS) as [VideoStyle, { label: string; description: string }][];

  return (
    <div className="grid grid-cols-3 gap-2.5">
      {styles.map(([style, info]) => {
        const isSelected = value === style;
        return (
          <button
            key={style}
            type="button"
            onClick={() => onChange(style)}
            className={cn(
              "relative flex flex-col items-start gap-1 p-3 rounded-lg border text-left transition-all duration-150",
              isSelected
                ? "border-primary bg-accent ring-1 ring-primary/20"
                : "border-border bg-background hover:bg-muted/40 hover:border-border"
            )}
          >
            {isSelected && (
              <span className="absolute top-2 right-2 flex items-center justify-center size-4 rounded-full bg-primary">
                <Check className="size-2.5 text-primary-foreground" />
              </span>
            )}
            <span className="text-lg leading-none">{STYLE_ICONS[style]}</span>
            <span className={cn("text-xs font-medium", isSelected ? "text-primary" : "text-foreground")}>
              {info.label}
            </span>
            <span className="text-[11px] text-muted-foreground leading-tight">
              {info.description}
            </span>
          </button>
        );
      })}
    </div>
  );
}
