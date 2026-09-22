"use client";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { type ColumnDef, flexRender, getCoreRowModel, getFilteredRowModel, getSortedRowModel, useReactTable, type SortingState, type VisibilityState } from "@tanstack/react-table";
import { cn } from "cn";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useInspector } from "@/components/inspector";

export type Col<T> = ColumnDef<T, any> & { header: string };

/** Registry table: sticky header, global search, sorting, column chooser (persisted), row click → inspector. The wrapper is the only allowed horizontal scroller. */
export function DataTable<T>({ columns, rows, getRowId, storageKey, renderDetail, labels, searchKeys }: {
  columns: Col<T>[]; rows: T[]; getRowId: (r: T) => string; storageKey: string; renderDetail: (r: T) => ReactNode; searchKeys: (keyof T)[];
  labels: { search: string; columns: string; rows: string; detail: string };
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [visibility, setVisibility] = useState<VisibilityState>({});
  const [selected, setSelected] = useState<string | null>(null);
  const inspector = useInspector();
  useEffect(() => { try { const v = localStorage.getItem(`logos.table.${storageKey}`); if (v) setVisibility(JSON.parse(v)); } catch {} }, [storageKey]);
  useEffect(() => { try { localStorage.setItem(`logos.table.${storageKey}`, JSON.stringify(visibility)); } catch {} }, [visibility, storageKey]);
  const table = useReactTable({
    data: rows, columns, state: { sorting, globalFilter, columnVisibility: visibility }, onSortingChange: setSorting, onGlobalFilterChange: setGlobalFilter, onColumnVisibilityChange: setVisibility,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(), getFilteredRowModel: getFilteredRowModel(), getRowId: (r) => getRowId(r),
    globalFilterFn: (row, _col, value) => { const v = String(value).toLowerCase(); return searchKeys.some((k) => String((row.original as any)[k] ?? "").toLowerCase().includes(v)); },
  });
  const n = table.getFilteredRowModel().rows.length;
  const open = (r: T) => { setSelected(getRowId(r)); inspector.open(renderDetail(r), `${labels.detail} · ${getRowId(r)}`); };
  const cols = useMemo(() => table.getAllLeafColumns(), [table]);
  return (
    <div className="min-w-0">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Input value={globalFilter} onChange={(e) => setGlobalFilter(e.target.value)} placeholder={labels.search} className="h-8 w-56 text-sm" aria-label={labels.search} />
        <span className="text-xs text-muted-foreground">{n} {labels.rows}</span>
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>{labels.columns}</DropdownMenuTrigger>
          <DropdownMenuContent align="start">{cols.map((c) => <DropdownMenuCheckboxItem key={c.id} checked={c.getIsVisible()} onCheckedChange={(v) => c.toggleVisibility(!!v)}>{(c.columnDef as Col<T>).header}</DropdownMenuCheckboxItem>)}</DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="max-h-[70vh] overflow-auto border border-border">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-muted text-left text-[0.65rem] uppercase tracking-widest text-muted-foreground">
            {table.getHeaderGroups().map((hg) => <tr key={hg.id}>{hg.headers.map((h) => <th key={h.id} className="cursor-pointer select-none whitespace-nowrap px-3 py-2 font-semibold" onClick={h.column.getToggleSortingHandler()}>{flexRender(h.column.columnDef.header, h.getContext())}{{ asc: " ▲", desc: " ▼" }[h.column.getIsSorted() as string] ?? ""}</th>)}</tr>)}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} onClick={() => open(row.original)} className={cn("cursor-pointer border-t border-border align-top hover:bg-muted/40", selected === row.id && "bg-muted/60")}>
                {row.getVisibleCells().map((cell) => <td key={cell.id} className={cn("max-w-[28rem] px-3 py-2", (cell.column.columnDef.meta as any)?.className)}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function Detail({ rows }: { rows: [string, ReactNode][] }) {
  return <dl className="grid gap-3">{rows.map(([k, v]) => <div key={k} className="min-w-0"><dt className="text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{k}</dt><dd className="mt-0.5 break-words">{v ?? "—"}</dd></div>)}</dl>;
}
