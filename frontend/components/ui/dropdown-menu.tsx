"use client";

import * as React from "react";
import { DropdownMenu as DropdownMenuPrimitive } from "radix-ui";

import { cn } from "@/lib/utils";

function DropdownMenu(props: React.ComponentProps<typeof DropdownMenuPrimitive.Root>) {
  return <DropdownMenuPrimitive.Root data-slot="dropdown-menu" {...props} />;
}

function DropdownMenuTrigger(
  props: React.ComponentProps<typeof DropdownMenuPrimitive.Trigger>,
) {
  return <DropdownMenuPrimitive.Trigger data-slot="dropdown-menu-trigger" {...props} />;
}

/**
 * Panel kiểu menu “⋮” trong video player: nền trắng, góc vuông, đổ bóng, item hover xám.
 */
function DropdownMenuContent({
  className,
  sideOffset = 6,
  align = "end",
  children,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Content>) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        data-slot="dropdown-menu-content"
        sideOffset={sideOffset}
        align={align}
        className={cn("z-[110] p-0 outline-none", className)}
        {...props}
      >
        <div
          className={cn(
            "dropdown-menu-player-surface min-w-[220px] origin-top-right overflow-hidden rounded-none border-0 bg-white py-1 text-sm text-neutral-900",
            "shadow-[0_4px_16px_rgba(0,0,0,0.18),0_0_1px_rgba(0,0,0,0.08)]",
            "dark:bg-neutral-900 dark:text-neutral-100 dark:shadow-[0_8px_32px_rgba(0,0,0,0.55)]",
            "will-change-[transform,opacity]",
          )}
        >
          {children}
        </div>
      </DropdownMenuPrimitive.Content>
    </DropdownMenuPrimitive.Portal>
  );
}

function DropdownMenuItem({
  className,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Item>) {
  return (
    <DropdownMenuPrimitive.Item
      data-slot="dropdown-menu-item"
      className={cn(
        "relative flex cursor-pointer select-none items-center gap-3 rounded-none px-4 py-3 outline-none",
        "text-neutral-900 dark:text-neutral-100",
        "data-[highlighted]:bg-neutral-200/95 data-[highlighted]:text-neutral-900",
        "dark:data-[highlighted]:bg-neutral-800 dark:data-[highlighted]:text-neutral-100",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-45",
        className,
      )}
      {...props}
    />
  );
}

function DropdownMenuSeparator({
  className,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Separator>) {
  return (
    <DropdownMenuPrimitive.Separator
      className={cn("my-0 h-px w-full bg-neutral-200 dark:bg-neutral-700", className)}
      {...props}
    />
  );
}

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
};
