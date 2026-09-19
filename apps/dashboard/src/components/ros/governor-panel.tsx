"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { errText, rosPost } from "@/lib/ros";

export function PreflightButton({ label }: { label: string }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  return (
    <span className="inline-flex items-center gap-2">
      <Button size="sm" disabled={busy} onClick={async () => { setBusy(true); const r = await rosPost("/api/ros/governor/preflight", {}); setBusy(false); setMsg(r.ok ? `${r.data.recorded.auth_class ?? "—"} · ${r.data.recorded.cli_version ?? "—"}` : errText(r)); if (r.ok) router.refresh(); }}>🔒 {label}</Button>
      {msg && <span className="font-mono text-xs text-muted-foreground" role="status">{msg}</span>}
    </span>
  );
}

export function QuotaReset({ label }: { label: string }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  return (
    <span className="inline-flex items-center gap-2">
      <Button size="sm" variant="outline" onClick={async () => { const r = await rosPost("/api/ros/governor/quota", { state: "OK", detail: "founder reset after subscription usage reset" }); setMsg(r.ok ? r.data.state : errText(r)); if (r.ok) router.refresh(); }}>🔒 {label}</Button>
      {msg && <span className="font-mono text-xs text-muted-foreground" role="status">{msg}</span>}
    </span>
  );
}
