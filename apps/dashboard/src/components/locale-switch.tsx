"use client";
import { useRouter } from "next/navigation";

export function LocaleSwitch({ locale }: { locale: "de" | "en" }) {
  const r = useRouter();
  const set = async (l: "de" | "en") => {
    await fetch("/api/locale", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ locale: l }) });
    r.refresh();
  };
  return (
    <div className="inline-flex border border-border text-[0.65rem] font-semibold uppercase tracking-widest" role="group" aria-label="Sprache / Language">
      {(["de", "en"] as const).map((l) => (
        <button key={l} type="button" onClick={() => set(l)} className={`px-2 py-1 ${locale === l ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground"}`}>{l.toUpperCase()}</button>
      ))}
    </div>
  );
}
