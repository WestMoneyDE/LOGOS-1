"use client";
import { useState } from "react";
import { API } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function ExportButton({ paperId }: { paperId: string }) {
  const [md, setMd] = useState<string | null>(null);
  return (
    <div>
      <Button variant="outline" onClick={async () => { const r = await fetch(`${API}/api/export/paper/${paperId}`); setMd((await r.json()).markdown); }}>Export research brief</Button>
      {md && <pre className="mt-3 max-h-[60vh] overflow-auto border border-border bg-muted/30 p-3 text-xs whitespace-pre-wrap">{md}</pre>}
    </div>
  );
}
