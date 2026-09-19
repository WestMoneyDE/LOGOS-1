import Link from "next/link";
import { cn } from "cn";

const NAV: [string, string][] = [["/", "Overview"], ["/tracks", "Tracks"], ["/claims", "Claims"], ["/theses", "Work on theses"], ["/falsification", "What could prove us wrong?"], ["/negative-results", "Negative results"],
  ["/experiments", "Experiments"], ["/invariants", "Invariants"], ["/counterexamples", "Counterexamples"], ["/replication", "Replication"], ["/publications", "Publications"], ["/prior-art", "Prior art"],
  ["/open-questions", "Open questions"], ["/research", "Deep research"], ["/timeline", "Timeline"], ["/reproducibility", "Reproducibility"], ["/p7", "P7 boundary"]];

export function Shell({ children, title, subtitle }: { children: React.ReactNode; title: string; subtitle?: string }) {
  return (
    <div className="flex min-h-screen w-full">
      <aside className="hidden w-60 shrink-0 border-r border-border p-5 md:block">
        <Link href="/" className="block font-heading text-lg font-semibold tracking-tight">LOGOS-1</Link>
        <p className="mt-1 text-xs text-muted-foreground">Research program dashboard</p>
        <nav className="mt-6 flex flex-col gap-1 text-sm">
          {NAV.map(([href, label]) => <Link key={href} href={href} className="rounded-sm px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground">{label}</Link>)}
        </nav>
        <p className="mt-8 text-[0.625rem] leading-relaxed text-muted-foreground">Every statement links to a repository record. Status ≠ strength of evidence. Nothing here is a claim about phenomenal consciousness (P7).</p>
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 md:px-10">
        <header className="mb-6 border-b border-border pb-4">
          <h1 className="font-heading text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{subtitle}</p>}
        </header>
        <div className="max-w-6xl">{children}</div>
      </main>
    </div>
  );
}

export function Section({ title, children, hint }: { title: string; children: React.ReactNode; hint?: string }) {
  return (
    <section className="mb-8">
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
