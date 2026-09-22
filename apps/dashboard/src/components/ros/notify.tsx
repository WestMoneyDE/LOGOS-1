"use client";
import { useEffect, useRef, useState } from "react";
import { API } from "@/lib/api";

const KEY = "logos.notify";

/** Local browser notifications: a waiting gate, a finished run, a quota stop. Polls the leitstand endpoint; no external service, nothing leaves the machine. */
export function NotifySwitch({ label, hint }: { label: string; hint: string }) {
  const [on, setOn] = useState(false); const seen = useRef<{ attention: number; runs: Record<string, string> }>({ attention: -1, runs: {} });
  useEffect(() => { try { setOn(localStorage.getItem(KEY) === "1" && typeof Notification !== "undefined" && Notification.permission === "granted"); } catch {} }, []);
  useEffect(() => {
    if (!on) return;
    const tick = async () => {
      try {
        const r = await fetch(`${API}/api/ros/leitstand`); if (!r.ok) return;
        const d = await r.json();
        const n = (d.attention ?? []).length;
        if (seen.current.attention >= 0 && n > seen.current.attention) new Notification("LOGOS-1: Entscheidung wartet", { body: (d.attention[0]?.text ?? "").slice(0, 160) });
        seen.current.attention = n;
        const run = d.live_run;
        if (run) {
          const prev = seen.current.runs[run.run_id];
          if (prev && prev !== run.state && run.state !== "running") new Notification(`LOGOS-1: Lauf ${run.state}`, { body: `${run.run_id} · ${run.kind}` });
          seen.current.runs[run.run_id] = run.state;
        }
        if (d.governor?.quota?.state && d.governor.quota.state !== "OK") new Notification("LOGOS-1: Quota erschöpft", { body: "Der Lauf wurde gestoppt. Nach dem Reset im System zurücksetzen." });
      } catch {}
    };
    const id = setInterval(tick, 15000); tick();
    return () => clearInterval(id);
  }, [on]);
  return (
    <label className="inline-flex flex-wrap items-center gap-2 text-xs">
      <input type="checkbox" checked={on} aria-label={label} onChange={async (e) => {
        const want = e.target.checked;
        if (want && typeof Notification !== "undefined" && Notification.permission !== "granted") {
          const p = await Notification.requestPermission();
          if (p !== "granted") { setOn(false); return; }
        }
        setOn(want); try { localStorage.setItem(KEY, want ? "1" : "0"); } catch {}
      }} />
      {label}
      <span className="basis-full text-[0.65rem] text-muted-foreground">{hint}</span>
    </label>
  );
}
