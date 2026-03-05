"use client";

import { cn } from "@/lib/utils";
import { VOICE_OPTIONS } from "@/lib/types";
import { Mic } from "lucide-react";

interface VoiceSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export function VoiceSelector({ value, onChange }: VoiceSelectorProps) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {VOICE_OPTIONS.map((voice) => {
        const isSelected = value === voice.value;
        return (
          <button
            key={voice.value}
            type="button"
            onClick={() => onChange(voice.value)}
            className={cn(
              "flex flex-col items-start gap-1.5 rounded-lg border p-3 text-left transition-all duration-150",
              isSelected
                ? "border-primary bg-primary/5 ring-1 ring-primary"
                : "border-border bg-background hover:border-border/80 hover:bg-muted/30"
            )}
          >
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex items-center justify-center size-6 rounded-md shrink-0",
                  isSelected ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
                )}
              >
                <Mic className="size-3" />
              </div>
              <span
                className={cn(
                  "text-xs font-semibold",
                  isSelected ? "text-primary" : "text-foreground"
                )}
              >
                {voice.label}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-tight pl-0.5">
              {voice.description}
            </p>
          </button>
        );
      })}
    </div>
  );
}
