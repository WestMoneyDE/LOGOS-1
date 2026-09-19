import { cn } from "cn";
import { getT, NAV } from "@/i18n";
import { SidebarNav } from "@/components/sidebar-nav";
import { InspectorFrame } from "@/components/inspector";

export async function Shell({ children, title, subtitle }: { children: React.ReactNode; title: string; subtitle?: string }) {
  const { locale, t } = await getT();
  const groups = NAV.map((g) => ({ label: t(g.area), items: g.items.map((it) => ({ href: it.href, label: t(it.key) })) }));
  return (
    <div className="flex min-h-screen w-full">
      <SidebarNav groups={groups} locale={locale} labels={{ title: t("app_title"), subtitle: t("app_subtitle"), collapse: t("nav_collapse"), expand: t("nav_expand"), open: t("nav_open"), footer: t("footer_rule") }} />
      <InspectorFrame labels={{ title: t("inspector_title"), close: "×" }}>
        <main className="min-w-0 px-4 pb-8 pt-14 md:px-8 md:pt-6">
          <header className="mb-6 border-b border-border pb-4">
            <h1 className="font-heading text-2xl font-semibold tracking-tight">{title}</h1>
            {subtitle && <p className="mt-1 max-w-4xl text-sm text-muted-foreground">{subtitle}</p>}
          </header>
          <div className="min-w-0">{children}</div>
        </main>
      </InspectorFrame>
    </div>
  );
}

export function Section({ title, children, hint }: { title: string; children: React.ReactNode; hint?: string }) {
  return (
    <section className="mb-8 min-w-0">
      <h2 className="mb-2 text-[0.7rem] font-semibold uppercase tracking-widest text-muted-foreground">{title}{hint && <span className="ml-2 normal-case tracking-normal font-normal">— {hint}</span>}</h2>
      {children}
    </section>
  );
}

export function Src({ path }: { path: string }) {
  return <code className="break-all font-mono text-[0.7rem] text-muted-foreground">{path}</code>;
}

export function Table({ head, rows, className }: { head: string[]; rows: React.ReactNode[][]; className?: string }) {
  return (
    <div className={cn("overflow-x-auto border border-border", className)}>
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left text-[0.65rem] uppercase tracking-widest text-muted-foreground"><tr>{head.map((h) => <th key={h} className="px-3 py-2 font-semibold">{h}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i} className="border-t border-border align-top">{r.map((c, j) => <td key={j} className="px-3 py-2">{c}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}
