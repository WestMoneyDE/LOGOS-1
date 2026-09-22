"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { errText, rosPost } from "@/lib/ros";

export function CreateThesis({ claim, existing, label }: { claim: { claim_id: string; title: string; track: string }; existing: boolean; label: string }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  if (existing) return null;
  return (
    <span className="inline-flex items-center gap-2">
      <Button size="sm" variant="outline" onClick={async () => { const r = await rosPost("/api/ros/theses", { thesis_id: `ROS-${claim.claim_id}`, claim_ids: [claim.claim_id], title: claim.title, track: claim.track, reason: "founder selection" }); setMsg(r.ok ? "ok" : errText(r)); if (r.ok) router.refresh(); }}>{label}</Button>
      {msg && msg !== "ok" && <span className="font-mono text-xs text-rose-700">{msg}</span>}
    </span>
  );
}
