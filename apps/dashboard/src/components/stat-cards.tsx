export function StatCards({ items }: { items: { label: string; value: string | number | null; sub?: string; pending?: boolean; href?: string }[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {items.map((it) => (
        <a key={it.label} href={it.href} className="min-w-0 border border-border p-3 hover:bg-muted/30">
          <div className="text-[0.62rem] uppercase tracking-widest text-muted-foreground">{it.label}</div>
          <div className="mt-1 font-heading text-2xl font-semibold">{it.value === null || it.value === undefined ? "—" : it.value}</div>
          <div className="mt-0.5 text-[0.65rem] text-muted-foreground">{it.pending ? "Phase 2/3" : it.sub ?? ""}</div>
        </a>
      ))}
    </div>
  );
}
