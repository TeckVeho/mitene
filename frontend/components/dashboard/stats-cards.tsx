"use client";

import { Card, CardContent } from "@/components/ui/card";
import { useJobStats } from "@/hooks/use-jobs";
import { FileVideo, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCard {
  label: string;
  value: number;
  icon: React.ElementType;
  iconClass: string;
  bgClass: string;
}

function StatCardSkeleton() {
  return (
    <Card className="border-border">
      <CardContent className="p-5">
        <div className="h-12 animate-pulse bg-muted rounded-md" />
      </CardContent>
    </Card>
  );
}

export function StatsCards() {
  const { data, isLoading } = useJobStats();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  const cards: StatCard[] = [
    {
      label: "総生成数",
      value: data?.total ?? 0,
      icon: FileVideo,
      iconClass: "text-muted-foreground",
      bgClass: "bg-muted/50",
    },
    {
      label: "処理中",
      value: data?.processing ?? 0,
      icon: Loader2,
      iconClass: "text-blue-600",
      bgClass: "bg-blue-50",
    },
    {
      label: "完了",
      value: data?.completed ?? 0,
      icon: CheckCircle,
      iconClass: "text-green-600",
      bgClass: "bg-green-50",
    },
    {
      label: "エラー",
      value: data?.error ?? 0,
      icon: AlertCircle,
      iconClass: "text-red-600",
      bgClass: "bg-red-50",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {cards.map((card) => (
        <Card key={card.label} className="border-border">
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-muted-foreground font-medium">{card.label}</span>
              <div className={cn("flex items-center justify-center size-7 rounded-md", card.bgClass)}>
                <card.icon className={cn("size-4", card.iconClass)} />
              </div>
            </div>
            <p className="text-2xl font-semibold text-foreground">{card.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
