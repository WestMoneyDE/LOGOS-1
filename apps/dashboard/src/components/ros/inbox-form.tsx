"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { errText, rosPost } from "@/lib/ros";

export function InboxForm({ kinds, labels }: { kinds: string[]; labels: { add: string; text: string; source: string; kind: string } }) {
  const router = useRouter(); const [kind, setKind] = useState(kinds[0] ?? "idea"); const [text, setText] = useState(""); const [source, setSource] = useState(""); const [msg, setMsg] = useState<string | null>(null);
  return (
    <div className="max-w-3xl border border-border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-xs text-muted-foreground">{labels.kind} <select aria-label={labels.kind} className="border border-border bg-background px-2 py-1 font-mono text-xs" value={kind} onChange={(e) => setKind(e.target.value)}>{kinds.map((k) => <option key={k}>{k}</option>)}</select></label>
        <Input className="h-8 max-w-xs text-xs" placeholder={labels.source} aria-label={labels.source} value={source} onChange={(e) => setSource(e.target.value)} />
      </div>
      <Textarea className="mt-2 text-sm" placeholder={labels.text} aria-label={labels.text} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="mt-2 flex items-center gap-2"><Button size="sm" disabled={!text.trim()} onClick={async () => { const r = await rosPost("/api/ros/inbox", { kind, text, source_ref: source || null, process: true }); setMsg(r.ok ? `#${r.data.item_id} → radar #${r.data.radar_id} ${r.data.radar.state} · ${r.data.radar.payload.action.delta_kind}` : errText(r)); if (r.ok) { setText(""); setSource(""); router.refresh(); } }}>{labels.add}</Button>{msg && <span className="font-mono text-xs text-muted-foreground" role="status">{msg}</span>}</div>
    </div>
  );
}
