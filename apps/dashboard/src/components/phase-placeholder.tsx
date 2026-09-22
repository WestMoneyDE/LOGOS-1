import { getT } from "@/i18n";
import { Shell } from "@/components/shell";

export async function PhasePlaceholder({ title, phase, spec, will }: { title: string; phase: number; spec: string; will: string[] }) {
  const { t } = await getT();
  return (
    <Shell title={title} subtitle={t("phase_note").replace("{n}", String(phase))}>
      <div className="max-w-3xl border border-border p-4 text-sm">
        <div className="text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{t("spec_section")}: {spec}</div>
        <ul className="mt-2 list-disc pl-5">{will.map((x) => <li key={x}>{x}</li>)}</ul>
      </div>
    </Shell>
  );
}
