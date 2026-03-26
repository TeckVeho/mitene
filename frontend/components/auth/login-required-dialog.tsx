"use client";

import Link from "next/link";
import { Dialog } from "radix-ui";
import { useLocale } from "@/lib/locale-context";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function LoginRequiredDialog({ open, onOpenChange }: Props) {
  const { t } = useLocale();

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-[2px]" />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-[101] w-[min(calc(100vw-2rem),24rem)] -translate-x-1/2 -translate-y-1/2 rounded-xl p-6 shadow-2xl outline-none",
            "border border-neutral-200 bg-white text-neutral-900",
            "dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100",
          )}
        >
          <Dialog.Title className="text-base font-semibold text-neutral-900 dark:text-neutral-50">
            {t.loginRequiredModal.title}
          </Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
            {t.loginRequiredModal.description}
          </Dialog.Description>
          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Dialog.Close asChild>
              <Button type="button" variant="outline" size="sm">
                {t.common.back}
              </Button>
            </Dialog.Close>
            <Button type="button" size="sm" asChild>
              <Link href="/login" onClick={() => onOpenChange(false)}>
                {t.common.login}
              </Link>
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
