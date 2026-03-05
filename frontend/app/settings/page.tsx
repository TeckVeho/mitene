import { ApiInfoPanel } from "@/components/settings/api-info";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">設定</h1>
        <p className="text-sm text-muted-foreground mt-1">
          外部システムから本サービスを利用するためのAPI情報を確認できます
        </p>
      </div>
      <ApiInfoPanel />
    </div>
  );
}
