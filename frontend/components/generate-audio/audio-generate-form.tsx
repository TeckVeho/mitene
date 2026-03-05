"use client";

import { useState } from "react";
import { useForm, Controller, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ChevronDown, ChevronUp, Mic, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { CsvUpload } from "@/components/generate/csv-upload";
import { VoiceSelector } from "./voice-selector";
import { useGenerateAudio } from "@/hooks/use-generate-audio";
import { cn } from "@/lib/utils";
import { INSTRUCTION_PRESETS, DEFAULT_PRESET_ID, getPresetById } from "@/lib/instruction-presets";

const schema = z.object({
  title: z.string().min(1, "タイトルを入力してください").max(100),
  instructions: z.string().min(1, "指示文を入力してください").max(2000),
  voiceName: z.string().min(1),
  language: z.string().min(1),
  timeout: z.coerce.number().min(60).max(3600),
});

type FormValues = z.infer<typeof schema>;

const LANGUAGES = [
  { value: "ja", label: "日本語" },
  { value: "en", label: "English" },
  { value: "zh_Hans", label: "中文（简体）" },
  { value: "ko", label: "한국어" },
];

function FormSection({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("space-y-3", className)}>
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      {children}
    </section>
  );
}

export function AudioGenerateForm() {
  const [csvFiles, setCsvFiles] = useState<File[]>([]);
  const [csvError, setCsvError] = useState<string>("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [selectedPresetId, setSelectedPresetId] = useState<string>(DEFAULT_PRESET_ID);
  const [ttsConfig, setTtsConfig] = useState(getPresetById(DEFAULT_PRESET_ID)?.ttsConfig ?? { stylePrompt: "" });
  const { mutate: generate, isPending } = useGenerateAudio();

  const defaultInstructions = getPresetById(DEFAULT_PRESET_ID)?.text ?? "";

  const {
    register,
    control,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema) as Resolver<FormValues>,
    defaultValues: {
      title: "ドライバー走行レポート",
      instructions: defaultInstructions,
      voiceName: "Kore",
      language: "ja",
      timeout: 600,
    },
  });

  const handlePresetChange = (presetId: string) => {
    setSelectedPresetId(presetId);
    const preset = getPresetById(presetId);
    if (preset && presetId !== "custom") {
      setValue("instructions", preset.text, { shouldValidate: true });
      setTtsConfig(preset.ttsConfig);
    }
  };

  const handleInstructionsChange = () => {
    setSelectedPresetId("custom");
  };

  const handleCsvChange = (files: File[]) => {
    setCsvFiles(files);
    if (files.length > 0) setCsvError("");
  };

  const onSubmit = (values: FormValues) => {
    if (csvFiles.length === 0) {
      setCsvError("CSVファイルを1つ以上選択してください");
      return;
    }
    generate({
      csvFiles,
      title: values.title,
      instructions: values.instructions,
      voiceName: values.voiceName,
      language: values.language,
      timeout: values.timeout,
      stylePrompt: ttsConfig.stylePrompt,
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-7">
      {/* CSV Upload */}
      <FormSection title="CSVファイル">
        <CsvUpload value={csvFiles} onChange={handleCsvChange} error={csvError} />
      </FormSection>

      <Separator />

      {/* Basic settings */}
      <FormSection title="基本設定">
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="title" className="text-xs text-muted-foreground font-medium">
              タイトル
            </Label>
            <Input
              id="title"
              placeholder="例: 埼玉営業所 202601 走行レポート"
              {...register("title")}
              className={cn(errors.title && "border-destructive")}
            />
            {errors.title && (
              <p className="text-xs text-destructive">{errors.title.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground font-medium">
              解説への指示文
            </Label>
            <Select value={selectedPresetId} onValueChange={handlePresetChange}>
              <SelectTrigger>
                <SelectValue placeholder="プリセットを選択" />
              </SelectTrigger>
              <SelectContent>
                {INSTRUCTION_PRESETS.map((preset) => (
                  <SelectItem key={preset.id} value={preset.id}>
                    {preset.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Textarea
              id="instructions"
              rows={4}
              placeholder="指示文を入力してください"
              {...register("instructions", { onChange: handleInstructionsChange })}
              className={cn("resize-none", errors.instructions && "border-destructive")}
            />
            {errors.instructions && (
              <p className="text-xs text-destructive">{errors.instructions.message}</p>
            )}
          </div>
        </div>
      </FormSection>

      <Separator />

      {/* Voice selection */}
      <FormSection title="ボイス選択">
        <Controller
          name="voiceName"
          control={control}
          render={({ field }) => (
            <VoiceSelector value={field.value} onChange={field.onChange} />
          )}
        />
      </FormSection>

      <Separator />

      {/* Advanced settings */}
      <section>
        <button
          type="button"
          onClick={() => setAdvancedOpen(!advancedOpen)}
          className="flex items-center gap-1.5 text-sm font-semibold text-foreground hover:text-muted-foreground transition-colors"
        >
          {advancedOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          詳細設定
        </button>

        {advancedOpen && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="language" className="text-xs text-muted-foreground font-medium">
                出力言語
              </Label>
              <Controller
                name="language"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="language">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LANGUAGES.map((lang) => (
                        <SelectItem key={lang.value} value={lang.value}>
                          {lang.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="timeout" className="text-xs text-muted-foreground font-medium">
                タイムアウト（秒）
              </Label>
              <Input
                id="timeout"
                type="number"
                min={60}
                max={3600}
                {...register("timeout")}
                className={cn(errors.timeout && "border-destructive")}
              />
              {errors.timeout && (
                <p className="text-xs text-destructive">{errors.timeout.message}</p>
              )}
            </div>
          </div>
        )}
      </section>

      {/* Submit */}
      <div className="pt-2">
        <Button
          type="submit"
          size="lg"
          disabled={isPending}
          className="w-full gap-2"
        >
          {isPending ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              処理中...
            </>
          ) : (
            <>
              <Mic className="size-4" />
              音声を生成する
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
