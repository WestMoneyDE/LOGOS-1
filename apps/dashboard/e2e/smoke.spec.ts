import { test, expect } from "@playwright/test";
import { ROUTES } from "./routes";
import { pageOverflow, clippedElements } from "./layout";
import * as fs from "fs";

// Smoke + layout QA for every core route (§58-63). Results are also written as a JSON inventory for /system/qa (§93).
const results: any[] = [];
// Live control-plane pages change while the behaviour specs (control-plane/executor) create TEST-ROS rows in parallel; they keep every layout gate but no pixel baseline.
const DYNAMIC = new Set(["/system/qa", "/queue", "/runs", "/theses", "/board", "/work-orders", "/decisions", "/system/workers", "/system/quotas", "/system/claude", "/traces", "/benchmarks", "/progress", "/inbox", "/radar", "/notes", "/reports"]);

for (const r of ROUTES) {
  test(`route ${r.path} renders, no overflow, no clipping, no console errors`, async ({ page }, testInfo) => {
    const consoleErrors: string[] = []; const failedRequests: string[] = [];
    page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 200)); });
    page.on("requestfailed", (q) => { const err = q.failure()?.errorText ?? ""; if (err === "net::ERR_ABORTED" && q.url().includes("_rsc=")) return; /* Next.js link prefetch cancelled on navigation */ failedRequests.push(`${q.method()} ${q.url()} ${err}`); });
    const t0 = Date.now();
    const resp = await page.goto(r.path, { waitUntil: "load" });
    await page.locator("main h1").first().waitFor();
    expect(resp?.status(), `HTTP status for ${r.path}`).toBe(200);
    await expect(page.locator("main").getByText(r.expect, { exact: false }).first()).toBeVisible();
    const ov = await pageOverflow(page);
    const clipped = await clippedElements(page);
    results.push({ route: r.path, project: testInfo.project.name, viewport: testInfo.project.use.viewport, status: resp?.status(), overflow: ov, clipped, consoleErrors, failedRequests, durationMs: Date.now() - t0 });
    await page.screenshot({ path: `e2e/results/screenshots/${testInfo.project.name}${r.path === "/" ? "/index" : r.path}.png`, fullPage: true });
    if (["desktop-1440", "mobile-390"].includes(testInfo.project.name) && !DYNAMIC.has(r.path)) await expect(page).toHaveScreenshot({ fullPage: true, mask: [page.locator("time")] });
    expect(ov.overflow, `page-level horizontal overflow on ${r.path} (${ov.scrollWidth} > ${ov.innerWidth})`).toBe(false);
    expect(clipped, `clipped key content on ${r.path}`).toEqual([]);
    expect(consoleErrors, `console errors on ${r.path}`).toEqual([]);
    expect(failedRequests, `failed requests on ${r.path}`).toEqual([]);
  });
}

test("theses selection roundtrip", async ({ page }) => {
  await page.goto("/theses");
  const box = page.getByRole("checkbox").first();
  const before = await box.isChecked();
  await box.click();
  await page.getByRole("button", { name: /Save selection/ }).click();
  await expect(page.getByText(/saved \d+ selected/)).toBeVisible();
  await box.click();                                                  // restore
  await page.getByRole("button", { name: /Save selection/ }).click();
  await expect(page.getByText(/saved \d+ selected/)).toBeVisible();
  expect(await box.isChecked()).toBe(before);
});

test.afterAll(async () => {
  fs.mkdirSync("e2e/results", { recursive: true });
  const file = "e2e/results/route-inventory.json";
  const prev = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf-8")) : [];
  fs.writeFileSync(file, JSON.stringify([...prev, ...results], null, 1));
});
