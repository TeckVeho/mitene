"use client";

import { Check, Circle, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { JobStepInfo } from "@/lib/types";

interface JobProgressProps {
  steps: JobStepInfo[];
}

function StepIcon({ status }: { status: JobStepInfo["status"] }) {
  if (status === "completed") {
    return (
      <div className="flex items-center justify-center size-7 rounded-full bg-green-100 border-2 border-green-500 shrink-0">
        <Check className="size-3.5 text-green-600" />
      </div>
    );
  }
  if (status === "in_progress") {
    return (
      <div className="flex items-center justify-center size-7 rounded-full bg-blue-50 border-2 border-blue-500 shrink-0">
        <Loader2 className="size-3.5 text-blue-600 animate-spin" />
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="flex items-center justify-center size-7 rounded-full bg-red-50 border-2 border-red-500 shrink-0">
        <X className="size-3.5 text-red-600" />
      </div>
    );
  }
  return (
    <div className="flex items-center justify-center size-7 rounded-full bg-muted border-2 border-border shrink-0">
      <Circle className="size-3 text-muted-foreground/50" />
    </div>
  );
}

export function JobProgress({ steps }: JobProgressProps) {
  return (
    <ol className="space-y-0">
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1;
        return (
          <li key={step.id} className="relative flex gap-4">
            {/* Connector line */}
            {!isLast && (
              <div
                className={cn(
                  "absolute left-[13px] top-7 bottom-0 w-0.5",
                  step.status === "completed" ? "bg-green-300" : "bg-border"
                )}
              />
            )}
            <StepIcon status={step.status} />
            <div className={cn("pb-6 min-w-0", isLast && "pb-0")}>
              <p
                className={cn(
                  "text-sm font-medium",
                  step.status === "in_progress"
                    ? "text-blue-700"
                    : step.status === "completed"
                    ? "text-foreground"
                    : step.status === "error"
                    ? "text-destructive"
                    : "text-muted-foreground"
                )}
              >
                {step.label}
              </p>
              {step.message && (
                <p
                  className={cn(
                    "text-xs mt-0.5",
                    step.status === "error" ? "text-destructive" : "text-muted-foreground"
                  )}
                >
                  {step.message}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
