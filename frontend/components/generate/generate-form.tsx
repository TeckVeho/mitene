"use client";

import { useState } from "react";
import { useForm, Controller, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ChevronDown, ChevronUp, Video, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { CsvUpload } from "./csv-upload";
import { StyleSelector } from "./style-selector";
import { FormatSelector } from "./format-selector";
import { useGenerateVideo } from "@/hooks/use-generate";
import { cn } from "@/lib/utils";

const schema = z.object({
  notebookTitle: z.string().min(1, "タイトルを入力してください").max(100),
  instructions: z.string().min(1, "指示文を入力してください").max(1000),
  style: z.enum(["auto", "classic", "whiteboard", "kawaii", "anime", "watercolor", "retro-print", "heritage", "paper-craft"]),
  format: z.enum(["explainer", "brief"]),
  language: z.string().min(1),
  timeout: z.coerce.number().min(60).max(7200),
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

export function GenerateForm() {
  const [csvFiles, setCsvFiles] = useState<File[]>([]);
  const [csvError, setCsvError] = useState<string>("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const { mutate: generate, isPending } = useGenerateVideo();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema) as Resolver<FormValues>,
    defaultValues: {
      notebookTitle: "CSV分析レポート",
      instructions: "CSVデータの主要な傾向と示唆を分かりやすく解説してください",
      style: "whiteboard",
      format: "explainer",
      language: "ja",
      timeout: 1800,
    },
  });

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
      notebookTitle: values.notebookTitle,
      instructions: values.instructions,
      style: values.style,
      format: values.format,
      language: values.language,
      timeout: values.timeout,
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-7">
      {/* CSV Upload */}
      <FormSection title="CSVファイル">
        <CsvUpload
          value={csvFiles}
          onChange={handleCsvChange}
          error={csvError}
        />
      </FormSection>

      <Separator />

      {/* Notebook settings */}
      <FormSection title="ノートブック設定">
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="notebookTitle" className="text-xs text-muted-foreground font-medium">
              タイトル
            </Label>
            <Input
              id="notebookTitle"
              placeholder="例: 埼玉営業所 202601 走行レポート"
              {...register("notebookTitle")}
              className={cn(errors.notebookTitle && "border-destructive")}
            />
            {errors.notebookTitle && (
              <p className="text-xs text-destructive">{errors.notebookTitle.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="instructions" className="text-xs text-muted-foreground font-medium">
              動画への指示文
            </Label>
            <Textarea
              id="instructions"
              rows={3}
              placeholder="例: CSVデータの主要な傾向と示唆を分かりやすく解説してください"
              {...register("instructions")}
              className={cn("resize-none", errors.instructions && "border-destructive")}
            />
            {errors.instructions && (
              <p className="text-xs text-destructive">{errors.instructions.message}</p>
            )}
          </div>
        </div>
      </FormSection>

      <Separator />

      {/* Style */}
      <FormSection title="ビジュアルスタイル">
        <Controller
          name="style"
          control={control}
          render={({ field }) => (
            <StyleSelector value={field.value} onChange={field.onChange} />
          )}
        />
      </FormSection>

      <Separator />

      {/* Format */}
      <FormSection title="動画フォーマット">
        <Controller
          name="format"
          control={control}
          render={({ field }) => (
            <FormatSelector value={field.value} onChange={field.onChange} />
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
                max={7200}
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
              <Video className="size-4" />
              動画を生成する
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
