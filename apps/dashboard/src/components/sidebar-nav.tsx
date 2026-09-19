"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "cn";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { LocaleSwitch } from "@/components/locale-switch";

export type NavGroup = { label: string; items: { href: string; label: string }[] };
type Labels = { title: string; subtitle: string; collapse: string; expand: string; open: string; footer: string };

function NavList({ groups, collapsed, onNavigate }: { groups: NavGroup[]; collapsed: boolean; onNavigate?: () => void }) {
  const path = usePathname();
  return (
    <nav className="flex flex-col gap-4 text-sm">
      {groups.map((g) => (
        <div key={g.label}>
          {!collapsed && <div className="mb-1 text-[0.6rem] font-semibold uppercase tracking-widest text-muted-foreground">{g.label}</div>}
          <div className="flex flex-col">
            {g.items.map((it) => {
              const active = it.href === "/" ? path === "/" : path.startsWith(it.href);
              return <Link key={it.href} href={it.href} onClick={onNavigate} title={it.label} className={cn("truncate rounded-sm px-2 py-0.5 hover:bg-muted hover:text-foreground", active ? "bg-muted font-medium text-foreground" : "text-muted-foreground")}>{collapsed ? it.label.slice(0, 2) : it.label}</Link>;
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

export function SidebarNav({ groups, labels, locale }: { groups: NavGroup[]; labels: Labels; locale: "de" | "en" }) {
  const [collapsed, setCollapsed] = useState(false); const [sheet, setSheet] = useState(false);
  useEffect(() => { try { setCollapsed(localStorage.getItem("logos.sidebar.collapsed") === "1"); } catch {} }, []);
  const toggle = () => { const v = !collapsed; setCollapsed(v); try { localStorage.setItem("logos.sidebar.collapsed", v ? "1" : "0"); } catch {} };
  return (
    <>
      <aside className={cn("hidden shrink-0 border-r border-border p-4 md:block", collapsed ? "w-16" : "w-60")}>
        <div className="flex items-center justify-between gap-2">
          {!collapsed && <Link href="/" className="font-heading text-lg font-semibold tracking-tight">{labels.title}</Link>}
          <Button variant="ghost" size="sm" aria-label={collapsed ? labels.expand : labels.collapse} onClick={toggle}>{collapsed ? "»" : "«"}</Button>
        </div>
        {!collapsed && <p className="mt-1 text-xs text-muted-foreground">{labels.subtitle}</p>}
        {!collapsed && <div className="mt-3"><LocaleSwitch locale={locale} /></div>}
        <div className="mt-5"><NavList groups={groups} collapsed={collapsed} /></div>
        {!collapsed && <p className="mt-8 text-[0.625rem] leading-relaxed text-muted-foreground">{labels.footer}</p>}
      </aside>
      <div className="fixed left-3 top-3 z-40 md:hidden">
        <Sheet open={sheet} onOpenChange={setSheet}>
          <SheetTrigger render={<Button variant="outline" size="sm" aria-label={labels.open}>☰ {labels.open}</Button>} />
          <SheetContent side="left" className="w-[85vw] overflow-y-auto p-4 sm:max-w-xs">
            <SheetHeader><SheetTitle>{labels.title}</SheetTitle></SheetHeader>
            <div className="mb-3"><LocaleSwitch locale={locale} /></div>
            <NavList groups={groups} collapsed={false} onNavigate={() => setSheet(false)} />
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
