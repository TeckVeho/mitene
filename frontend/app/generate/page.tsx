import { GenerateForm } from "@/components/generate/generate-form";

export default function GeneratePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">新規動画生成</h1>
        <p className="text-sm text-muted-foreground mt-1">
          CSVファイルをアップロードして、AI解説動画を生成します
        </p>
      </div>
      <GenerateForm />
    </div>
  );
}
