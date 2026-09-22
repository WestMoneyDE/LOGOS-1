"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { errText, rosPost } from "@/lib/ros";

export function PaperExport({ paperId, label }: { paperId: string; label: string }) {
  const [msg, setMsg] = useState<string | null>(null);
  return <span className="inline-flex items-center gap-2"><Button size="sm" variant="outline" onClick={async () => { const r = await rosPost(`/api/ros/papers/${paperId}/export`, {}); setMsg(r.ok ? `${r.data.path} · ${r.data.sha256.slice(0, 12)} · Reifegrad unverändert (${r.data.manuscript_status_unchanged})` : errText(r)); }}>{label}</Button>{msg && <span className="font-mono text-[0.65rem] text-muted-foreground" role="status">{msg}</span>}</span>;
}
