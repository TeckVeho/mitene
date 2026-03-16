export { ja } from "./ja";
export { vi } from "./vi";
export type { Locale, Translations } from "./types";

import { ja } from "./ja";
import { vi } from "./vi";
import type { Locale } from "./types";

export const translations: Record<Locale, typeof ja> = {
  ja,
  vi,
};
