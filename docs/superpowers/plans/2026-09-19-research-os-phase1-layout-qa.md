# Research OS — Phase 1 (Layout, IA, DE/EN, DataTable + Inspector, QA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the read-only scientific dashboard into the Research-OS shell: five-area German navigation with EN switch, dense desktop layout with resizable inspector, DataTables that never overflow the page, a QA page fed by Playwright, and a Command Center skeleton — all Playwright-gated.

**Architecture:** Next.js App Router pages stay server components that fetch the FastAPI service; a small i18n dictionary (`src/i18n/*.ts`) and a cookie-based locale switch replace hard-coded English labels; shared `DataTable` + `Inspector` components replace the ad-hoc `Table`; Playwright gets visual snapshots and writes the route inventory that `/system/qa` renders through a new API endpoint.

**Tech Stack:** Next.js 16.3, React 19, Tailwind 4, shadcn preset `b1abNSlea` (base-sera), `@playwright/test` 1.63, FastAPI service `src/logos_dashboard`, pytest.

## Global Constraints
- Scientific vocabulary (statuses, verdicts, claim ids, hashes) stays English; UI labels default to German, EN switchable (founder decision).
- `NO PAGE-LEVEL HORIZONTAL OVERFLOW`, `NO CLIPPED SCIENTIFIC CONTENT`, `NO IMPORTANT INFORMATION HIDDEN BY ELLIPSIS` (order §2); horizontal scrollers only inside DataTables/graph canvases.
- Every core route must pass the Playwright projects `desktop-1920 desktop-1440 desktop-1366 desktop-1280 tablet-1024 mobile-390` (order §58–63).
- No forbidden words in UI copy (`PROVEN`, `BREAKTHROUGH`, `REVOLUTIONARY`, …); status ≠ strength stays visible.
- The dashboard remains TOOLING; no model call; no credential in the browser.
- Existing routes keep working (redirects allowed, no deletions; order §95).
- Run services for e2e: `PYTHONPATH=src .venv/Scripts/python.exe -m uvicorn logos_dashboard.api:app --host 127.0.0.1 --port 8765` and `cd apps/dashboard && pnpm exec next build && pnpm exec next start -p 3000`.

---

### Task 1: i18n dictionary and locale switch

**Files:**
- Create: `apps/dashboard/src/i18n/de.ts`, `apps/dashboard/src/i18n/en.ts`, `apps/dashboard/src/i18n/index.ts`
- Create: `apps/dashboard/src/components/locale-switch.tsx`
- Create: `apps/dashboard/src/app/api/locale/route.ts`
- Test: `apps/dashboard/e2e/i18n.spec.ts`

**Interfaces:**
- Produces: `t(key: keyof Dict): string` (server: `getT()` reads the `logos_locale` cookie; client: `useT()`), `type Locale = "de" | "en"`, `NAV: {area: string; items: {href: string; key: keyof Dict}[]}[]`.

- [ ] **Step 1: Write the failing e2e test**

```ts
// apps/dashboard/e2e/i18n.spec.ts
import { test, expect } from "@playwright/test";
test("German is default, EN switch persists", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("aside").getByText("Kommandozentrale")).toBeVisible();
  await page.getByRole("button", { name: "EN" }).click();
  await expect(page.locator("aside").getByText("Command Center")).toBeVisible();
  await page.goto("/claims");
  await expect(page.locator("main h1")).toHaveText(/Claim registry/);
  await page.getByRole("button", { name: "DE" }).click();
  await expect(page.locator("main h1")).toHaveText(/Claim-Register/);
});
```

- [ ] **Step 2: Run it to verify it fails** — `cd apps/dashboard && pnpm exec playwright test e2e/i18n.spec.ts --project=desktop-1440` → FAIL ("Kommandozentrale" not visible).

- [ ] **Step 3: Implement the dictionary**

```ts
// apps/dashboard/src/i18n/de.ts
export const de = {
  app_title: "LOGOS-1", app_subtitle: "Forschungsbetriebssystem",
  area_operate: "Betrieb", area_analyze: "Analyse", area_knowledge: "Wissen", area_publish: "Publizieren", area_system: "System",
  nav_command_center: "Kommandozentrale", nav_theses: "Thesen", nav_work_orders: "Work Orders", nav_queue: "Warteschlange", nav_runs: "Live-Läufe", nav_decisions: "Entscheidungen", nav_inbox: "Eingang", nav_radar: "Radar",
  nav_traces: "Traces", nav_experiments: "Experimente", nav_benchmarks: "Benchmarks", nav_progress: "Monatsfortschritt", nav_statistics: "Statistik", nav_negative: "Negativergebnisse", nav_counterexamples: "Gegenbeispiele", nav_replication: "Replikation",
  nav_claims: "Claims", nav_invariants: "Invarianten", nav_graph: "Evidenzgraph", nav_prior_art: "Prior Art", nav_open_questions: "Offene Fragen", nav_timeline: "Zeitleiste", nav_reproducibility: "Reproduzierbarkeit", nav_p7: "P7-Grenze", nav_tracks: "Tracks",
  nav_publications: "Publikationen", nav_exports: "Export", nav_artifacts: "Artefakte", nav_research: "Deep Research",
  nav_mlflow: "MLflow", nav_workers: "Worker", nav_claude: "Claude-Auth", nav_quotas: "Quoten", nav_governance: "Governance", nav_qa: "Playwright-QA", nav_health: "Systemzustand", nav_settings: "Einstellungen",
  claims_title: "Claim-Register", claims_subtitle: "Status der Hypothese ≠ Evidenzstärke; beides wird gezeigt. Status kommen nur aus dem Register, nie aus Freitext.",
  footer_rule: "Jede Aussage verweist auf einen Repository-Record. Status ≠ Evidenzstärke. Nichts hier ist eine Aussage über phänomenales Bewusstsein (P7).",
  not_extracted: "nicht extrahiert", scope: "Geltungsbereich", copy: "kopieren", inspector_empty: "Zeile auswählen, um Details zu sehen.",
} as const;
export type Dict = typeof de;
```
```ts
// apps/dashboard/src/i18n/en.ts
import type { Dict } from "./de";
export const en: Dict = { app_title: "LOGOS-1", app_subtitle: "Research operating system", area_operate: "Operate", area_analyze: "Analyze", area_knowledge: "Knowledge", area_publish: "Publish", area_system: "System",
  nav_command_center: "Command Center", nav_theses: "Theses", nav_work_orders: "Work Orders", nav_queue: "Run Queue", nav_runs: "Live Runs", nav_decisions: "Decisions / Gates", nav_inbox: "Research Inbox", nav_radar: "Radar Inbox",
  nav_traces: "Traces", nav_experiments: "Experiments", nav_benchmarks: "Benchmarks", nav_progress: "Monthly Progress", nav_statistics: "Statistics", nav_negative: "Negative Results", nav_counterexamples: "Counterexamples", nav_replication: "Replication",
  nav_claims: "Claims", nav_invariants: "Invariants", nav_graph: "Evidence Graph", nav_prior_art: "Prior Art", nav_open_questions: "Open Questions", nav_timeline: "Timeline", nav_reproducibility: "Reproducibility", nav_p7: "P7 Boundary", nav_tracks: "Tracks",
  nav_publications: "Publications", nav_exports: "Export / Research Briefs", nav_artifacts: "Artifacts", nav_research: "Deep Research",
  nav_mlflow: "MLflow", nav_workers: "Workers", nav_claude: "Claude Auth Status", nav_quotas: "Quotas", nav_governance: "Governance", nav_qa: "Playwright QA", nav_health: "System Health", nav_settings: "Settings",
  claims_title: "Claim registry", claims_subtitle: "Status of hypothesis ≠ strength of evidence; both are shown. Statuses come only from the registry, never from free text.",
  footer_rule: "Every statement links to a repository record. Status ≠ strength of evidence. Nothing here is a claim about phenomenal consciousness (P7).",
  not_extracted: "not extracted", scope: "Scope", copy: "copy", inspector_empty: "Select a row to see details." };
```
```ts
// apps/dashboard/src/i18n/index.ts
import { cookies } from "next/headers";
import { de, type Dict } from "./de";
import { en } from "./en";
export type Locale = "de" | "en";
export const DICTS: Record<Locale, Dict> = { de, en };
export async function getLocale(): Promise<Locale> { const c = (await cookies()).get("logos_locale")?.value; return c === "en" ? "en" : "de"; }
export async function getT() { const l = await getLocale(); const d = DICTS[l]; return { locale: l, t: (k: keyof Dict) => d[k] }; }
export const NAV: { area: keyof Dict; items: { href: string; key: keyof Dict }[] }[] = [
  { area: "area_operate", items: [{ href: "/", key: "nav_command_center" }, { href: "/theses", key: "nav_theses" }, { href: "/work-orders", key: "nav_work_orders" }, { href: "/queue", key: "nav_queue" }, { href: "/runs", key: "nav_runs" }, { href: "/decisions", key: "nav_decisions" }, { href: "/inbox", key: "nav_inbox" }, { href: "/radar", key: "nav_radar" }] },
  { area: "area_analyze", items: [{ href: "/traces", key: "nav_traces" }, { href: "/experiments", key: "nav_experiments" }, { href: "/benchmarks", key: "nav_benchmarks" }, { href: "/progress", key: "nav_progress" }, { href: "/statistics", key: "nav_statistics" }, { href: "/negative-results", key: "nav_negative" }, { href: "/counterexamples", key: "nav_counterexamples" }, { href: "/replication", key: "nav_replication" }] },
  { area: "area_knowledge", items: [{ href: "/claims", key: "nav_claims" }, { href: "/invariants", key: "nav_invariants" }, { href: "/falsification", key: "nav_graph" }, { href: "/prior-art", key: "nav_prior_art" }, { href: "/open-questions", key: "nav_open_questions" }, { href: "/timeline", key: "nav_timeline" }, { href: "/reproducibility", key: "nav_reproducibility" }, { href: "/p7", key: "nav_p7" }, { href: "/tracks", key: "nav_tracks" }] },
  { area: "area_publish", items: [{ href: "/publications", key: "nav_publications" }, { href: "/research", key: "nav_research" }] },
  { area: "area_system", items: [{ href: "/system/qa", key: "nav_qa" }, { href: "/system/health", key: "nav_health" }, { href: "/system/governance", key: "nav_governance" }] },
];
```
```ts
// apps/dashboard/src/app/api/locale/route.ts
import { NextResponse } from "next/server";
export async function POST(req: Request) {
  const { locale } = await req.json();
  const res = NextResponse.json({ locale: locale === "en" ? "en" : "de" });
  res.cookies.set("logos_locale", locale === "en" ? "en" : "de", { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" });
  return res;
}
```
```tsx
// apps/dashboard/src/components/locale-switch.tsx
"use client";
import { useRouter } from "next/navigation";
export function LocaleSwitch({ locale }: { locale: "de" | "en" }) {
  const r = useRouter();
  const set = async (l: "de" | "en") => { await fetch("/api/locale", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ locale: l }) }); r.refresh(); };
  return <div className="inline-flex border border-border text-[0.65rem] font-semibold uppercase tracking-widest">{(["de", "en"] as const).map((l) => <button key={l} onClick={() => set(l)} className={`px-2 py-1 ${locale === l ? "bg-foreground text-background" : "text-muted-foreground"}`}>{l.toUpperCase()}</button>)}</div>;
}
```
Nav items whose routes do not exist yet (work-orders, queue, runs, decisions, inbox, radar, traces, benchmarks, progress, statistics, system/health, system/governance) are wired in Task 6 as placeholder pages that say "Phase N" — never a 404 in the sidebar.

- [ ] **Step 4: Use it in the shell** — modify `apps/dashboard/src/components/shell.tsx`: `Shell` becomes `async`, calls `const { locale, t } = await getT()`, renders `NAV` groups with `t(area)` headings and `t(key)` labels, adds `<LocaleSwitch locale={locale} />` under the title, and prints `t("footer_rule")`. Modify `apps/dashboard/src/app/claims/page.tsx` to use `t("claims_title")` / `t("claims_subtitle")`.

- [ ] **Step 5: Run the test** — `pnpm exec next build && pnpm exec next start -p 3000 &` then `pnpm exec playwright test e2e/i18n.spec.ts --project=desktop-1440` → PASS.

- [ ] **Step 6: Commit** — `git add apps/dashboard/src/i18n apps/dashboard/src/components/locale-switch.tsx apps/dashboard/src/app/api/locale apps/dashboard/src/components/shell.tsx apps/dashboard/src/app/claims/page.tsx apps/dashboard/e2e/i18n.spec.ts && git commit -m "dashboard: German default with EN switch; five-area navigation"`

---

### Task 2: Responsive shell — collapsible sidebar, mobile sheet, full-width main, resizable inspector slot

**Files:**
- Modify: `apps/dashboard/src/components/shell.tsx`
- Create: `apps/dashboard/src/components/sidebar-nav.tsx` (client: collapse state in `localStorage`, `Sheet` on `< md`)
- Create: `apps/dashboard/src/components/inspector.tsx` (client: right panel, `Resizable` from shadcn, `localStorage` width)
- Test: `apps/dashboard/e2e/shell.spec.ts`

**Interfaces:**
- Produces: `<Shell title subtitle inspector?: ReactNode>`; `<Inspector open onOpenChange width>` with `useInspector()` context (`open(content: ReactNode)`, `close()`).

- [ ] **Step 1: Install components** — `pnpm dlx shadcn@latest add resizable sheet dropdown-menu breadcrumb skeleton alert popover -y`.

- [ ] **Step 2: Write the failing e2e test**

```ts
// apps/dashboard/e2e/shell.spec.ts
import { test, expect } from "@playwright/test";
test("mobile: sidebar is a sheet, no overflow", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile-390");
  await page.goto("/claims");
  await expect(page.locator("aside")).toBeHidden();
  await page.getByRole("button", { name: /Navigation/ }).click();
  await expect(page.getByRole("dialog").getByText("Claims")).toBeVisible();
});
test("desktop: sidebar collapses and main uses full width", async ({ page }, info) => {
  test.skip(!info.project.name.startsWith("desktop"));
  await page.goto("/claims");
  const before = await page.locator("main").boundingBox();
  await page.getByRole("button", { name: /Einklappen|Collapse/ }).click();
  const after = await page.locator("main").boundingBox();
  expect(after!.width).toBeGreaterThan(before!.width + 100);
});
```

- [ ] **Step 3: Run to verify it fails** — `pnpm exec playwright test e2e/shell.spec.ts --project=mobile-390 --project=desktop-1440` → FAIL (no Navigation button).

- [ ] **Step 4: Implement** — `sidebar-nav.tsx`: props `{groups: {label: string; items: {href: string; label: string}[]}[]; locale}`; state `collapsed` (persisted under `logos.sidebar.collapsed`); renders `<aside className={collapsed ? "w-14" : "w-60"}>` on `md+` with a `Button` labelled `Einklappen`/`Collapse` (aria-label by locale) and, on `< md`, a `Button` `Navigation` opening a `Sheet` with the same groups. `inspector.tsx`: `InspectorProvider` (context with `content`, `open`, `close`), `InspectorPanel` rendered by `Shell` as the right pane of a `ResizablePanelGroup` (`direction="horizontal"`, default sizes 70/30, min 20) only when content is set; on `< lg` it renders as a `Sheet side="right"`. `Shell`: `<div className="flex min-h-screen w-full">` + `<SidebarNav/>` + `<main className="min-w-0 flex-1">` (remove the `max-w-6xl` cap; keep a 16px gutter).

- [ ] **Step 5: Run the test + the full smoke** — `pnpm exec playwright test` → all green (no overflow on 6 viewports).

- [ ] **Step 6: Commit** — `git commit -am "dashboard: collapsible sidebar, mobile sheet, resizable inspector, full-width main"`

---

### Task 3: DataTable with inspector, short hashes, column chooser, search, sort

**Files:**
- Create: `apps/dashboard/src/components/data-table.tsx` (client; `@tanstack/react-table`)
- Create: `apps/dashboard/src/components/hash.tsx` (`<Hash value>` → first 10 chars, copy button, full value in tooltip)
- Modify: `apps/dashboard/src/app/claims/page.tsx`, `apps/dashboard/src/app/experiments/page.tsx`, `apps/dashboard/src/app/invariants/page.tsx` (table → DataTable + inspector detail)
- Test: `apps/dashboard/e2e/datatable.spec.ts`

**Interfaces:**
- Produces: `<DataTable columns rows getRowId searchKeys onRowSelect storageKey>`; `<Hash value/>`.

- [ ] **Step 1: Install** — `pnpm add @tanstack/react-table`.

- [ ] **Step 2: Write the failing e2e test**

```ts
// apps/dashboard/e2e/datatable.spec.ts
import { test, expect } from "@playwright/test";
test("experiments table: search, sort, inspector, short hash", async ({ page }) => {
  await page.goto("/experiments");
  await page.getByPlaceholder(/Suchen|Search/).fill("CPA-RERUN");
  await expect(page.getByRole("row")).toHaveCount(2);                      // header + 1
  await expect(page.getByText(/^99525f856a/)).toBeVisible();                // short hash
  await page.getByRole("row").nth(1).click();
  await expect(page.getByRole("complementary").getByText("99525f856ae0653c99e97804bba1b7d00abf7565c3439b63e9a0fd5ed051786e")).toBeVisible();   // full hash in inspector
});
```

- [ ] **Step 3: Run to verify it fails** — `pnpm exec playwright test e2e/datatable.spec.ts --project=desktop-1440` → FAIL.

- [ ] **Step 4: Implement `data-table.tsx`** — `useReactTable` with `getCoreRowModel`, `getSortedRowModel`, `getFilteredRowModel`, global filter over `searchKeys`; sticky header (`thead` `sticky top-0 bg-background`); `DropdownMenu` column chooser persisted in `localStorage[storageKey]`; container `<div className="overflow-x-auto border border-border">` (the only allowed horizontal scroller); row click → `onRowSelect(row)` → page passes content to `useInspector().open(...)`. `hash.tsx`: `<Tooltip>` with full value, `navigator.clipboard.writeText` on copy, `aria-label="copy"`. Pages: claims columns `id, title, track, status (StatusBadge), strength (StrengthBadge), kind, scope (line-clamp-2 with full text in inspector)`; experiments columns `id, track, verdict, kind, negative, prereg (Hash), run, record (Src)`; invariants columns `id, statement, track, class, status, kind` — each with an inspector rendering the complete record (all fields, no clipping).

- [ ] **Step 5: Run test + full smoke** — `pnpm exec playwright test` → PASS on all projects.

- [ ] **Step 6: Commit** — `git commit -am "dashboard: DataTable with inspector, search, sort, column chooser, short hashes"`

---

### Task 4: Playwright visual snapshots + route inventory endpoint + `/system/qa`

**Files:**
- Modify: `apps/dashboard/e2e/smoke.spec.ts` (add `await expect(page).toHaveScreenshot(...)` for `desktop-1440` and `mobile-390` only; `--update-snapshots` to create baselines)
- Create: `apps/dashboard/e2e/visual.spec.ts` (screens of order §102 that exist in Phase 1: `/`, `/claims`, `/experiments`, `/system/qa`)
- Modify: `src/logos_dashboard/api.py` (add `GET /api/qa/last-run` reading `apps/dashboard/e2e/results/route-inventory.json` + `last-run.json`)
- Create: `apps/dashboard/src/app/system/qa/page.tsx`
- Test: `tests/test_dashboard_scientific_core.py::test_qa_endpoint`

**Interfaces:**
- Produces: `GET /api/qa/last-run → {last_run: {startTime, duration, expected, unexpected, flaky}, routes: [{route, project, status, overflow, clipped, consoleErrors, failedRequests, durationMs}], screenshots: [paths]}`.

- [ ] **Step 1: Write the failing pytest**

```python
def test_qa_endpoint():
    r = client.get("/api/qa/last-run"); assert r.status_code == 200
    body = r.json(); assert "routes" in body and "last_run" in body and isinstance(body["routes"], list)
```

- [ ] **Step 2: Run** — `pytest tests/test_dashboard_scientific_core.py::test_qa_endpoint -q` → FAIL 404.

- [ ] **Step 3: Implement** in `api.py`:

```python
QA_DIR = ROOT / "apps/dashboard/e2e/results"

@app.get("/api/qa/last-run")
def qa_last_run():
    inv = QA_DIR / "route-inventory.json"; last = QA_DIR / "last-run.json"
    routes = json.loads(inv.read_text(encoding="utf-8")) if inv.exists() else []
    stats = json.loads(last.read_text(encoding="utf-8")).get("stats", {}) if last.exists() else {}
    shots = sorted(str(p.relative_to(QA_DIR)).replace("\\", "/") for p in (QA_DIR / "screenshots").rglob("*.png")) if (QA_DIR / "screenshots").exists() else []
    return {"last_run": stats, "routes": routes, "screenshots": shots, "projects": sorted({r["project"] for r in routes}),
            "violations": [r for r in routes if r.get("overflow", {}).get("overflow") or r.get("clipped") or r.get("consoleErrors") or r.get("failedRequests")]}
```
(`ROOT` is imported from `.registries`.) Page `system/qa/page.tsx`: cards (last run time, expected/unexpected/flaky, routes tested, violations), a DataTable of routes × projects (status, overflow, clipped count, console errors, duration), and the screenshot list grouped by project (served by copying `e2e/results/screenshots` into `public/qa/` in the e2e `afterAll`, or linking to the HTML report path).

- [ ] **Step 4: Visual snapshots** — in `smoke.spec.ts` after the layout checks: `if (["desktop-1440", "mobile-390"].includes(testInfo.project.name)) await expect(page).toHaveScreenshot({ fullPage: true, mask: [page.locator("time")] });` Run once with `pnpm exec playwright test --update-snapshots --project=desktop-1440 --project=mobile-390` to create baselines under `e2e/smoke.spec.ts-snapshots/`; commit them.

- [ ] **Step 5: Run everything** — `pytest tests/test_dashboard_scientific_core.py -q` PASS; `pnpm exec playwright test` PASS; `curl 127.0.0.1:3000/system/qa` 200.

- [ ] **Step 6: Commit** — `git add -A && git commit -m "qa: visual snapshots, route inventory endpoint, /system/qa page"`

---

### Task 5: Command Center skeleton (Phase-1 scope) and shadcn charts

**Files:**
- Modify: `apps/dashboard/src/app/page.tsx`
- Create: `apps/dashboard/src/components/stat-cards.tsx`, `apps/dashboard/src/components/charts/verdict-mix.tsx` (shadcn `ChartContainer` + Recharts `BarChart`)
- Modify: `src/logos_dashboard/api.py` (`GET /api/command-center` → counts, active theses with next test, open decisions from closures, alerts list [integrity violations, records-only, missing artifacts], verdict mix by month from experiment registry + closures)
- Test: `tests/test_dashboard_scientific_core.py::test_command_center_endpoint`, e2e `e2e/command-center.spec.ts`

**Interfaces:**
- Produces: `GET /api/command-center → {stats: {active_theses, queued_work_orders: 0, running_agents: 0, blocked_gates, experiments_this_month, negative_results_this_month, publication_candidates, integrity_violations, records_only}, active_research: [{claim_id, title, track, status, next_test}], alerts: [{kind, text, href}], verdict_mix: [{month, supported, partial, falsified, invalid}]}`. Queue/agents fields are literal 0 until Phase 2/3 fill them (the UI labels them "Phase 2").

- [ ] **Step 1: Install chart** — `pnpm dlx shadcn@latest add chart -y` (installs `recharts`).

- [ ] **Step 2: Failing tests**

```python
def test_command_center_endpoint():
    b = client.get("/api/command-center").json()
    assert {"stats", "active_research", "alerts", "verdict_mix"} <= set(b) and b["stats"]["queued_work_orders"] == 0
```
```ts
// e2e/command-center.spec.ts
import { test, expect } from "@playwright/test";
test("command center shows stats, alerts and verdict chart", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/Aktive Thesen|Active theses/)).toBeVisible();
  await expect(page.locator("svg.recharts-surface").first()).toBeVisible();
});
```

- [ ] **Step 3: Run both → FAIL.** — `pytest … -q`; `pnpm exec playwright test e2e/command-center.spec.ts --project=desktop-1440`.

- [ ] **Step 4: Implement** — `api.py` endpoint computing `verdict_mix` from `readers.closures()` (month = `closed[:7]`, class via `verdict_class`), `active_research` from `ACTIVE-THESES.json` joined with claims, `alerts` from `registries.validate()`, lab `records_only`, and experiments with `run_id` but empty `artifact_hash`. Page: `StatCards` (10 cards per order §4, zeros labelled "Phase 2"), `Active Research` cards (thesis id/title/track/status/next test/risk placeholder), `Research Alerts` list, `VerdictMix` bar chart with `ChartContainer`, `ChartTooltip`, N shown in the card header (`n = Σ closures`), and a note "deterministische Fixtures — kein KI" where no CI applies.

- [ ] **Step 5: Run tests + smoke** — all PASS.

- [ ] **Step 6: Commit** — `git commit -am "dashboard: command center skeleton with stat cards, alerts and verdict-mix chart"`

---

### Task 6: Placeholder pages for Phase 2–7 routes and redirects (no 404 in the sidebar)

**Files:**
- Create: `apps/dashboard/src/app/{work-orders,queue,runs,decisions,inbox,radar,traces,benchmarks,progress,statistics}/page.tsx`, `apps/dashboard/src/app/system/{health,governance}/page.tsx`
- Modify: `apps/dashboard/e2e/routes.ts` (add the new routes with expect text "Phase")
- Test: existing `smoke.spec.ts` covers them.

- [ ] **Step 1: Add routes to `routes.ts`** (expect: `Phase 2` … `Phase 7` per spec phase; `/system/health` expects "Systemzustand"; `/system/governance` expects "Governance").
- [ ] **Step 2: Run smoke → FAIL 404** for the new routes.
- [ ] **Step 3: Implement** each page with `Shell` + a `Card` stating the phase, the spec section, and what it will show; `/system/health` renders `/api/health` (records_only, lab error, git branch/head, integrity violations) as cards; `/system/governance` renders `/api/registries`-independent data from `/api/registries/claims` tracks + `INFERENCE-GOVERNANCE.json` via a new `GET /api/governance-record` (returns G1–G4 active, superseded, flag whitelist, caps).
- [ ] **Step 4: Run smoke on all projects → PASS.**
- [ ] **Step 5: Commit** — `git commit -am "dashboard: phase placeholders, system health and governance pages"`

---

### Task 7: Phase-1 gate — full matrix, screenshots, classification, commit

- [ ] **Step 1:** `pnpm exec next build && pnpm exec next start -p 3000 &`; `pnpm exec playwright test` → 0 unexpected across 6 projects.
- [ ] **Step 2:** Review `e2e/results/screenshots/{desktop-1920,desktop-1440,desktop-1280,tablet-1024,mobile-390}/index.png`, `claims.png`, `experiments.png`, `system/qa.png` (order §102 subset for Phase 1).
- [ ] **Step 3:** `pytest tests/test_dashboard_scientific_core.py -q` PASS; register new files in `docs/research/DASHBOARD-SOURCE-CLASSIFICATION.json` and the four living classifications (class TOOLING / GOVERNANCE_ONLY); `pytest tests -q` full suite green.
- [ ] **Step 4:** `git commit -am "research-os: Phase 1 complete — IA, DE/EN, DataTable+inspector, QA page, command center skeleton"` and push.
