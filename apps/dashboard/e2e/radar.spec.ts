import { test, expect, request } from "@playwright/test";

// Phase 6: inbox capture -> deterministic radar analysis -> founder review; agent cannot review. TEST-ROS rows removed afterwards.
const API = process.env.LOGOS_API ?? "http://127.0.0.1:8765";

test.describe.serial("inbox + radar", () => {
  let api: Awaited<ReturnType<typeof request.newContext>>;
  test.beforeAll(async ({}, info) => { test.skip(info.project.name !== "desktop-1440", "behaviour on one viewport"); api = await request.newContext({ baseURL: API }); const st = await (await api.get("/api/ros/status")).json(); test.skip(st.records_only, "lab Postgres unreachable"); });
  test.afterAll(async () => { if (!api) return; await api.delete("/api/ros/radar/test-items"); await api.dispose(); });

  test("capture a paper, see the delta, accept it as founder", async ({ page }) => {
    await page.goto("/inbox", { waitUntil: "load" });
    await page.getByLabel("Art").selectOption("paper");
    await page.getByLabel("Text (URL/DOI/Claim-ID werden erkannt)").fill("TEST-ROS e2e paper on authority delegation https://example.org/e2e relevant to LOGOS-AUTH-001");
    await page.getByRole("button", { name: "Eintragen" }).click();
    await expect(page.getByRole("status")).toContainText("ACTION_PROPOSED · prior_art");
    await page.goto("/radar", { waitUntil: "load" });
    const card = page.locator("[data-radar]", { hasText: "TEST-ROS e2e paper" }).first();
    await expect(card.getByText("WHAT WOULD FALSIFY IT")).toBeVisible();
    await expect(card.getByText("PROPOSED (prior_art)")).toBeVisible();
    await card.getByRole("button", { name: "🔒 Annehmen" }).click();
    await expect(card.getByRole("status")).toContainText("ACCEPTED");
    await expect(page.locator("[data-radar]", { hasText: "TEST-ROS e2e paper" }).first()).toContainText("radar-drafts/");
  });
});
