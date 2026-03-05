export type InstructionPreset = {
  id: string;
  label: string;
  text: string;
};

export const INSTRUCTION_PRESETS: InstructionPreset[] = [
  {
    id: "summary",
    label: "走行実績サマリー",
    text: "各ドライバーの走行距離・走行時間・燃料消費量の主要指標をまとめ、全体平均と比較した際の特徴を分かりやすく説明してください。特に数値が際立つドライバーについては、その要因や背景についても触れてください。",
  },
  {
    id: "safety",
    label: "安全運転評価",
    text: "急ブレーキ・急加速・速度超過などの安全指標を分析し、特に改善が必要なドライバーと優秀なドライバーを具体的な数値を挙げて伝えてください。改善が必要なドライバーには具体的なアドバイスも含めてください。",
  },
  {
    id: "fuel",
    label: "燃費・エコ走行",
    text: "ドライバー別の燃費を分析し、燃費が良い・悪い原因を特定して、具体的な改善アドバイスをドライバーに向けて分かりやすく解説してください。エコ走行のポイントや省燃費運転のコツも合わせて説明してください。",
  },
  {
    id: "idling",
    label: "アイドリング・時間外",
    text: "アイドリング時間と時間外運行の状況を分析し、コスト削減につながる改善ポイントをドライバーに伝わるよう具体的に説明してください。特にアイドリングが多いドライバーには、削減によるコスト効果も示してください。",
  },
  {
    id: "custom",
    label: "その他（カスタム入力）",
    text: "",
  },
];

export const DEFAULT_PRESET_ID = "summary";

export function getPresetById(id: string): InstructionPreset | undefined {
  return INSTRUCTION_PRESETS.find((p) => p.id === id);
}
