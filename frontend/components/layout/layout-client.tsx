"use client";

import { useState, createContext, useContext } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";

interface SidebarContextType {
  open: boolean;
  toggle: () => void;
}

export const SidebarContext = createContext<SidebarContextType>({
  open: true,
  toggle: () => {},
});

export function useSidebar() {
  return useContext(SidebarContext);
}

export function LayoutClient({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(true);

  return (
    <SidebarContext.Provider value={{ open, toggle: () => setOpen((v) => !v) }}>
      <div className="flex flex-col h-screen overflow-hidden bg-white dark:bg-[#0f0f0f]">
        <Header />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto bg-white dark:bg-[#0f0f0f]">
            {children}
          </main>
        </div>
      </div>
    </SidebarContext.Provider>
  );
}
