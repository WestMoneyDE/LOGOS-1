"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { rosPost } from "@/lib/ros";

export function Notes({ thesisId, notes, labels }: { thesisId: string; notes: { note_id: number; author: string; text: string; decision_flag: boolean; consumed_by_job: number | null; created_at: string }[]; labels: { placeholder: string; add: string; flag: string } }) {
  const router = useRouter(); const [text, setText] = useState(""); const [flag, setFlag] = useState(false);
  return (
    <div className="max-w-3xl">
      <ul className="flex flex-col gap-1 text-sm">{notes.map((n) => <li key={n.note_id} className="border border-border p-2"><span className="font-mono text-[0.65rem] text-muted-foreground">#{n.note_id} · {n.author} · {n.created_at.slice(0, 16).replace("T", " ")}{n.decision_flag ? " · ⚑" : ""}{n.consumed_by_job ? ` · job ${n.consumed_by_job}` : ""}</span><br />{n.text}</li>)}</ul>
      <Textarea className="mt-2 text-sm" placeholder={labels.placeholder} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="mt-2 flex items-center gap-3">
        <Button size="sm" disabled={!text.trim()} onClick={async () => { const r = await rosPost("/api/ros/notes", { thesis_id: thesisId, text, decision_flag: flag }); if (r.ok) { setText(""); setFlag(false); router.refresh(); } }}>{labels.add}</Button>
        <label className="inline-flex items-center gap-1 text-xs"><input type="checkbox" checked={flag} onChange={(e) => setFlag(e.target.checked)} /> {labels.flag}</label>
      </div>
    </div>
  );
}
