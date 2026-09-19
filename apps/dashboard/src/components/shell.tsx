import Link from "next/link";
import { cn } from "cn";
import { getT, NAV } from "@/i18n";
import { LocaleSwitch } from "@/components/locale-switch";

export async function Shell({ children, title, subtitle }: { children: React.ReactNode; title: string; subtitle?: string }) {
  const { locale, t } = await getT();
  return (
    <div className="flex min-h-screen w-full">
      <aside className="hidden w-60 shrink-0 border-r border-border p-5 md:block">
        <Link href="/" className="block font-heading text-lg font-semibold tracking-tight">{t("app_title")}</Link>
        <p className="mt-1 text-xs text-muted-foreground">{t("app_subtitle")}</p>
        <div className="mt-3"><LocaleSwitch locale={locale} /></div>
        <nav className="mt-5 flex flex-col gap-4 text-sm">
          {NAV.map((g) => (
            <div key={g.area}>
              <div className="mb-1 text-[0.6rem] font-semibold uppercase tracking-widest text-muted-foreground">{t(g.area)}</div>
              <div className="flex flex-col">
                {g.items.map((it) => <Link key={it.href} href={it.href} className="rounded-sm px-2 py-0.5 text-muted-foreground hover:bg-muted hover:text-foreground">{t(it.key)}</Link>)}
              </div>
            </div>
          ))}
        </nav>
        <p className="mt-8 text-[0.625rem] leading-relaxed text-muted-foreground">{t("footer_rule")}</p>
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 md:px-8">
        <header className="mb-6 border-b border-border pb-4">
          <h1 className="font-heading text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-1 max-w-4xl text-sm text-muted-foreground">{subtitle}</p>}
        </header>
        <div className="min-w-0">{children}</div>
      </main>
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
