"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { errText, rosPost } from "@/lib/ros";

export function ReportFreeze({ month, label, frozen }: { month: string; label: string; frozen: boolean }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  return <span className="inline-flex items-center gap-2"><Button size="sm" variant="outline" disabled={frozen} onClick={async () => { const r = await rosPost(`/api/ros/reports/${month}/freeze`, {}); setMsg(r.ok ? `${r.data.path} · ${r.data.sha256.slice(0, 12)}` : errText(r)); if (r.ok) router.refresh(); }}>🔒 {label}</Button>{frozen && <span className="font-mono text-xs text-emerald-700">frozen</span>}{msg && <span className="font-mono text-xs text-muted-foreground" role="status">{msg}</span>}</span>;
}
