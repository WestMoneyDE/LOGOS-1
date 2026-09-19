import { test, expect, request } from "@playwright/test";

// Phase 5: benchmark lab renders NO_DATA honestly for agent modes; statistics calculator computes without inference; founder-only gates hold.
const API = process.env.LOGOS_API ?? "http://127.0.0.1:8765";

test.describe("benchmark lab + statistics", () => {
  test.beforeEach(async ({}, info) => { test.skip(info.project.name !== "desktop-1440", "behaviour on one viewport"); });

  test("benchmarks page shows six suites with NO_DATA agent cells and hard gates", async ({ page }) => {
    const api = await request.newContext({ baseURL: API }); const st = await (await api.get("/api/ros/status")).json(); test.skip(st.records_only, "lab Postgres unreachable"); await api.dispose();
    await page.goto("/benchmarks", { waitUntil: "load" });
    await expect(page.locator("[data-suite]")).toHaveCount(6);
    const auth = page.locator("[data-suite=AUTHORITY_GOLDEN]");
    await expect(auth.getByText("NO_DATA").first()).toBeVisible();
    await expect(auth.getByText("Hard Gates")).toBeVisible();
  });

  test("statistics calculator: wilson result carries method/n/version; bad input is rejected", async ({ page }) => {
    await page.goto("/statistics", { waitUntil: "load" });
    await page.getByLabel("method").selectOption("wilson");
    await page.getByLabel("args").fill('{"k": 45, "n": 60}');
    await page.getByRole("button", { name: "Berechnen" }).click();
    await expect(page.getByRole("status")).toContainText('"method": "wilson"');
    await expect(page.getByRole("status")).toContainText('"version": "ros-stats/1"');
    await page.getByLabel("args").fill('{"k": 70, "n": 60}');
    await page.getByRole("button", { name: "Berechnen" }).click();
    await expect(page.getByRole("status")).toContainText("k must satisfy");
  });

  test("progress page renders Wilson rates and the freeze button is founder-gated at the API", async ({ page }) => {
    const api = await request.newContext({ baseURL: API, extraHTTPHeaders: { "X-Logos-Actor": "agent" } }); const st = await (await api.get("/api/ros/status")).json(); test.skip(st.records_only, "lab Postgres unreachable");
    expect((await api.post("/api/ros/progress/freeze?month=1999-01")).status()).toBe(403); await api.dispose();
    await page.goto("/progress", { waitUntil: "load" });
    await expect(page.getByText("Falsifikationsrate")).toBeVisible();
    await expect(page.getByText("Wilson 95 %-KI", { exact: false }).first()).toBeVisible();
  });
});
