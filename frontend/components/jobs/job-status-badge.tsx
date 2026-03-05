import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

interface JobStatusBadgeProps {
  status: JobStatus;
  className?: string;
}

const STATUS_CONFIG: Record<JobStatus, { label: string; className: string }> = {
  pending: {
    label: "待機中",
    className: "bg-gray-100 text-gray-600 border-gray-200",
  },
  processing: {
    label: "処理中",
    className: "bg-blue-50 text-blue-700 border-blue-200",
  },
  completed: {
    label: "完了",
    className: "bg-green-50 text-green-700 border-green-200",
  },
  error: {
    label: "エラー",
    className: "bg-red-50 text-red-700 border-red-200",
  },
};

export function JobStatusBadge({ status, className }: JobStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium border", config.className, className)}
    >
      {config.label}
    </Badge>
  );
}
