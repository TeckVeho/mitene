import { AudioGenerateForm } from "@/components/generate-audio/audio-generate-form";

export default function GenerateAudioPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">新規音声生成</h1>
        <p className="text-sm text-muted-foreground mt-1">
          CSVファイルをアップロードして、Gemini AIによる音声解説ファイルを生成します
        </p>
      </div>
      <AudioGenerateForm />
    </div>
  );
}
