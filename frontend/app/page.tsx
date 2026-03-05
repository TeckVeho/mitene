import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentJobs } from "@/components/dashboard/recent-jobs";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">ダッシュボード</h1>
        <p className="text-sm text-muted-foreground mt-1">
          CSVファイルからAI解説動画を生成・管理します
        </p>
      </div>
      <StatsCards />
      <RecentJobs />
    </div>
  );
}
