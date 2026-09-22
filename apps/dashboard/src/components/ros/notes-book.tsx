"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { errText, rosPost } from "@/lib/ros";

export function NotesBook({ notes, label }: { notes: any[]; label: string }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  return (
    <div className="max-w-4xl">
      {msg && <p className="mb-2 font-mono text-xs text-muted-foreground" role="status">{msg}</p>}
      <ul className="flex flex-col gap-1 text-sm">{notes.map((n) => (
        <li key={n.note_id} className="flex flex-wrap items-start gap-2 border border-border p-2">
          <span className="font-mono text-[0.65rem] text-muted-foreground">#{n.note_id} · {n.author} · {String(n.created_at).slice(0, 16).replace("T", " ")}{n.decision_flag ? " · ⚑" : ""}{n.consumed_by_job ? ` · job ${n.consumed_by_job}` : ""}</span>
          {n.thesis_id && <Link className="font-mono text-[0.65rem] underline" href={`/theses/${n.thesis_id}`}>{n.thesis_id}</Link>}
          <span className="basis-full">{n.text}</span>
          <Button size="sm" variant="ghost" onClick={async () => { const r = await rosPost("/api/ros/inbox", { kind: "observation", text: n.text, source_ref: `note #${n.note_id}${n.thesis_id ? ` / ${n.thesis_id}` : ""}`, process: true }); setMsg(r.ok ? `note #${n.note_id} → radar #${r.data.radar_id}` : errText(r)); if (r.ok) router.refresh(); }}>{label}</Button>
        </li>))}</ul>
    </div>
  );
}
