"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";

type Ctx = { content: ReactNode | null; title: string; open: (content: ReactNode, title?: string) => void; close: () => void };
const InspectorCtx = createContext<Ctx>({ content: null, title: "", open: () => {}, close: () => {} });
export const useInspector = () => useContext(InspectorCtx);

/** Right-hand inspector: resizable pane on lg+, sheet below. Content is set by pages (e.g. a DataTable row). */
export function InspectorFrame({ children, labels }: { children: ReactNode; labels: { title: string; close: string } }) {
  const [content, setContent] = useState<ReactNode | null>(null);
  const [title, setTitle] = useState(labels.title);
  const ctx: Ctx = { content, title, open: (c, t) => { setContent(c); setTitle(t ?? labels.title); }, close: () => setContent(null) };
  const [large, setLarge] = useState(false);
  useEffect(() => { const mq = window.matchMedia("(min-width: 1024px)"); const f = () => setLarge(mq.matches); f(); mq.addEventListener("change", f); return () => mq.removeEventListener("change", f); }, []);
  const panel = (
    <aside aria-label={title} role="complementary" className="h-full overflow-y-auto border-l border-border p-4 text-sm">
      <div className="mb-3 flex items-center justify-between"><h2 className="font-heading text-sm font-semibold">{title}</h2><Button variant="ghost" size="sm" onClick={ctx.close}>{labels.close}</Button></div>
      {content}
    </aside>
  );
  return (
    <InspectorCtx.Provider value={ctx}>
      <div className="min-w-0 flex-1">
        {content && large ? (
          <ResizablePanelGroup orientation="horizontal" className="min-h-screen">
            <ResizablePanel defaultSize={66} minSize={40}>{children}</ResizablePanel>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={34} minSize={20}>{panel}</ResizablePanel>
          </ResizablePanelGroup>
        ) : children}
        {!large && (
          <Sheet open={!!content} onOpenChange={(o) => { if (!o) ctx.close(); }}>
            <SheetContent side="right" className="w-[92vw] overflow-y-auto p-4 sm:max-w-md" aria-label={title}>
              <SheetHeader><SheetTitle>{title}</SheetTitle></SheetHeader>
              <div role="complementary" className="text-sm">{content}</div>
            </SheetContent>
          </Sheet>
        )}
      </div>
    </InspectorCtx.Provider>
  );
}
