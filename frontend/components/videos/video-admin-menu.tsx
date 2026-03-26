"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Dialog } from "radix-ui";
import { Loader2, MoreVertical, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/locale-context";
import { cn } from "@/lib/utils";
import type { Video } from "@/lib/types";

type Props = { video: Video };

export function VideoAdminMenu({ video }: Props) {
  const { t } = useLocale();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [menuOpen, setMenuOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [draftTitle, setDraftTitle] = useState(video.title);
  const [draftDescription, setDraftDescription] = useState(video.description ?? "");

  useEffect(() => {
    if (!editOpen) return;
    setDraftTitle(video.title);
    setDraftDescription(video.description ?? "");
  }, [editOpen, video]);

  const patchMutation = useMutation({
    mutationFn: () =>
      api.patchAdminVideo(video.id, {
        title: draftTitle,
        description: draftDescription,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["videos", video.id], updated);
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      queryClient.invalidateQueries({ queryKey: ["admin-articles"] });
      setMenuOpen(false);
      setEditOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteAdminVideo(video.id),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["videos", video.id] });
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      queryClient.invalidateQueries({ queryKey: ["admin-articles"] });
      router.push("/");
    },
  });

  const openEdit = () => {
    setMenuOpen(false);
    setTimeout(() => setEditOpen(true), 0);
  };

  const requestDelete = () => {
    setMenuOpen(false);
    setTimeout(() => {
      if (!window.confirm(t.admin.confirmDeleteVideo)) return;
      deleteMutation.mutate();
    }, 0);
  };

  const handleEditDialogOpenChange = (open: boolean) => {
    setEditOpen(open);
    if (!open) setMenuOpen(false);
  };

  return (
    <>
      <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-9 shrink-0 rounded-full text-neutral-700 hover:bg-neutral-200/80 dark:text-neutral-200 dark:hover:bg-neutral-800"
            aria-label={t.videoDetail.adminMenuAria}
          >
            <MoreVertical className="size-5 stroke-[1.75]" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault();
              openEdit();
            }}
          >
            <Pencil className="size-[18px] shrink-0 stroke-[1.75] text-neutral-800 dark:text-neutral-200" />
            {t.admin.editVideo}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-red-600 data-[highlighted]:bg-red-50 data-[highlighted]:text-red-700 dark:text-red-400 dark:data-[highlighted]:bg-red-950/50 dark:data-[highlighted]:text-red-300"
            disabled={deleteMutation.isPending}
            onSelect={(e) => {
              e.preventDefault();
              requestDelete();
            }}
          >
            <Trash2 className="size-[18px] shrink-0 stroke-[1.75]" />
            {t.admin.deleteVideo}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog.Root open={editOpen} onOpenChange={handleEditDialogOpenChange}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-[2px]" />
          <Dialog.Content
            className={cn(
              "fixed left-1/2 top-1/2 z-[101] w-[min(calc(100vw-2rem),26rem)] max-h-[min(calc(100vh-2rem),90vh)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl p-6 shadow-2xl outline-none",
              "border border-neutral-200 bg-white text-neutral-900",
              "dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100",
            )}
          >
            <Dialog.Title className="text-base font-semibold text-neutral-900 dark:text-neutral-50">
              {t.admin.editVideo}
            </Dialog.Title>
            <Dialog.Description className="sr-only">{t.admin.videosListHint}</Dialog.Description>
            <div className="mt-4 space-y-3">
              <div className="space-y-2">
                <Label htmlFor="video-admin-title">{t.admin.videoTitleLabel}</Label>
                <Input
                  id="video-admin-title"
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="video-admin-desc">{t.admin.videoDescriptionLabel}</Label>
                <Textarea
                  id="video-admin-desc"
                  value={draftDescription}
                  onChange={(e) => setDraftDescription(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Dialog.Close asChild>
                <Button type="button" variant="outline" size="sm">
                  {t.admin.cancelEdit}
                </Button>
              </Dialog.Close>
              <Button
                type="button"
                size="sm"
                className="gap-1.5"
                disabled={patchMutation.isPending || !draftTitle.trim()}
                onClick={() => patchMutation.mutate()}
              >
                {patchMutation.isPending ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : null}
                {t.admin.saveVideo}
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
