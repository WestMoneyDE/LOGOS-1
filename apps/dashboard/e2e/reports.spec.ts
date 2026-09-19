import { test, expect } from "@playwright/test";

// Phase 7: monthly report renders deterministically; evidence debt lists records; freeze is founder-only (API) and never triggered by the test.
test.describe("reports", () => {
  test.beforeEach(async ({}, info) => { test.skip(info.project.name !== "desktop-1440", "behaviour on one viewport"); });
  test("monthly report + paper readiness + evidence debt", async ({ page }) => {
    await page.goto("/reports?month=2026-09", { waitUntil: "load" });
    await expect(page.getByLabel("monthly report")).toContainText("# LOGOS-1 Monthly Report — 2026-09");
    await expect(page.getByLabel("monthly report")).toContainText("Does not claim");
    await expect(page.getByText("PAPER-1", { exact: false }).first()).toBeVisible();
    await page.goto("/evidence-debt", { waitUntil: "load" });
    await expect(page.getByText("CLAIM-REGISTRY.json#", { exact: false }).first()).toBeVisible();
  });
});
